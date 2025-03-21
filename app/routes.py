import logging
from flask import Blueprint, request, jsonify
from flask_cors import CORS
import os
import tempfile
import shutil
from modules.database import database as db
from modules.database.database import (
    PaperNotFoundError,
    FileHashError,
    DatabaseError,
    EmbeddingNotFoundError,
    InvalidUpdateError,
    DuplicatePaperError,
)
from modules.latex_parser import reference_parser, latex_content_parser
from modules.storage.storage import S3UploadError
from modules.ollama import ollama_client
from modules.retriever.arxiv import arxiv_retriever

# Configure logger
logger = logging.getLogger(__name__)
# Create the main blueprint
bp = Blueprint("main", __name__)
# Enable CORS for all routes in this blueprint
CORS(bp)


@bp.route("/")
def home():
    """Simple endpoint to verify the API is running."""
    return jsonify({"message": "API is running"})


@bp.route("/papers", methods=["POST"])
def create_paper():
    """
    Upload and process a new paper.

    This endpoint handles:
    1. PDF file upload validation
    2. ArXiv metadata retrieval
    3. LaTeX content extraction and conversion to Markdown (if ArXiv source available)
    4. Reference extraction
    5. Paper storage in database and S3

    Returns:
        JSON with paper_id on success, error message on failure
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are allowed"}), 400

    title = request.form.get("title", "")
    authors = request.form.get("authors", "")

    try:
        # Save the uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            file.save(temp_file.name)
            # Try to get metadata from arxiv
            paper_metadata = arxiv_retriever.paper_get_metadata(temp_file.name)
            arxiv_paper_id = paper_metadata.get("arxiv_id", None)
            title: str = paper_metadata.get("title", title)
            authors: str = paper_metadata.get("authors", authors)
            abstract: str = paper_metadata.get("abstract", "")
            paper_url: str = paper_metadata.get("url", "")
            published: str = paper_metadata.get("published_date", "")
            updated: str = paper_metadata.get("updated_date", "")

            markdown_content = None
            references = []
            # Extract references, for now only from arxiv papers
            if arxiv_paper_id:
                try:
                    logger.info(f"Starting reference extraction for ArXiv paper {arxiv_paper_id}")
                    # Create a temporary directory for the paper source
                    temp_dir = tempfile.mkdtemp()
                    try:
                        # Download the paper source to the temporary directory
                        logger.debug(f"Downloading source files for ArXiv paper {arxiv_paper_id}")
                        arxiv_retriever.paper_download_arxiv_id(arxiv_paper_id, temp_dir)

                        # Extract the folder name which matches the arxiv ID
                        source_dir = os.path.join(temp_dir, arxiv_paper_id.replace(".", ""))
                        if not os.path.exists(source_dir):
                            # If the specific folder doesn't exist, use the base temp dir
                            logger.debug(f"Source directory {source_dir} not found, using base temp directory")
                            source_dir = temp_dir

                        # First create a markdown version of the paper
                        try:
                            logger.debug(f"Converting LaTeX to Markdown in directory: {source_dir}")
                            markdown_content = latex_content_parser.parse_latex_to_markdown(source_dir)
                            logger.info(f"Successfully created markdown version for paper {arxiv_paper_id}")
                        except Exception as e:
                            logger.warning(f"Failed to create markdown version: {str(e)}")
                            # Continue with original LaTeX files
                            markdown_content = None

                        # Extract references from the downloaded source
                        logger.debug(f"Extracting references from source directory: {source_dir}")
                        references = reference_parser.extract_references(source_dir)
                        logger.info(f"Successfully extracted {len(references)} references from paper {arxiv_paper_id}")
                    except arxiv_retriever.ArxivRetrievalError as e:
                        logger.error(f"ArXiv retrieval error for paper {arxiv_paper_id}: {str(e)}")
                        # Continue without references
                    except arxiv_retriever.ArxivDownloadError as e:
                        logger.error(f"ArXiv download error for paper {arxiv_paper_id}: {str(e)}")
                        # Continue without references
                    except arxiv_retriever.ExtractionError as e:
                        logger.error(f"Source extraction error for paper {arxiv_paper_id}: {str(e)}")
                        # Continue without references
                    except Exception as e:
                        logger.error(f"Unexpected error extracting references for paper {arxiv_paper_id}: {str(e)}")
                        # Continue without references
                    finally:
                        # Clean up: remove the temporary directory and its contents
                        try:
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            logger.info(f"Cleaned up temporary directory for {arxiv_paper_id}")
                        except Exception as e:
                            logger.warning(f"Failed to clean up temporary directory for {arxiv_paper_id}: {str(e)}")
                except Exception as e:
                    logger.error(f"Error in reference extraction process for paper {arxiv_paper_id}: {str(e)}")
                    # Continue the process even if reference extraction fails
            else:
                # TODO Extract references from the PDF itself
                logger.debug("No ArXiv ID found for paper, skipping reference extraction")

            # Insert the paper into the database
            paper_id = db.paper_insert(temp_file.name, title, authors, abstract, paper_url, published, updated, markdown_content)
            # Clean up the temporary file
            os.unlink(temp_file.name)

            # Insert references into database
            if references:
                try:
                    db.paper_references_insert_many(paper_id, references)
                    logger.info(f"Stored {len(references)} references for paper {paper_id}")
                except DatabaseError as e:
                    logger.error(f"Failed to store references for paper {paper_id}: {str(e)}")
                    # We don't want to fail the entire paper upload if reference storage fails

        return jsonify({"paper_id": paper_id}), 201
    except DuplicatePaperError as e:
        return jsonify({"error": str(e)}), 409
    except FileHashError as e:
        return jsonify({"error": str(e)}), 400
    except S3UploadError as e:
        return jsonify({"error": str(e)}), 503
    except DatabaseError as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/papers/<string:paper_id>/references", methods=["GET"])
def get_paper_references(paper_id):
    """Get all references for a specific paper."""
    try:
        references = db.paper_references_list(paper_id)
        return jsonify(references)
    except PaperNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DatabaseError as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/papers", methods=["GET"])
def list_papers():
    """
    List papers with optional similarity search.

    Query parameters:
        query (str): Optional search query to find similar papers
        page (int): Page number for pagination (default: 1)
        page_size (int): Number of papers per page (default: 10)

    Returns:
        JSON with papers list and pagination metadata
    """
    query = request.args.get("query")
    # Validate and normalize page and page_size
    try:
        page = max(1, int(request.args.get("page", 1)))
        page_size = max(1, int(request.args.get("page_size", 10)))
    except ValueError:
        page = 1
        page_size = 10

    try:
        if query:
            # Generate embedding for the search query
            query_embedding = ollama_client.get_query_embeddings(query)
            # Search for similar papers
            papers = db.paper_get_similar_to_query(query_embedding)
            # Format the response to exclude large embedding vectors
            formatted_papers = [
                {
                    "paper_id": paper["id"],
                    "title": paper["title"],
                    "authors": paper["authors"],
                    "abstract": paper.get("abstract", ""),
                    "online_url": paper.get("online_url", ""),
                    "published_date": paper.get("published_date", ""),
                    "updated_date": paper.get("updated_date", ""),
                    "created_at": paper.get("created_at", ""),
                    "similarity": paper["similarity"],
                }
                for paper in papers
            ]
            return jsonify({"papers": formatted_papers, "total": len(formatted_papers), "page": 1, "total_pages": 1})
        else:
            # Get paginated list of all papers
            result = db.paper_list_all(page=page, page_size=page_size)
            return jsonify(result)

    except EmbeddingNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DatabaseError as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/papers/<string:paper_id>", methods=["GET"])
def get_paper(paper_id):
    """Get a specific paper by its ID."""
    try:
        paper = db.paper_find(paper_id)

        if "embedding" in paper:
            del paper["embedding"]

        return jsonify(paper)
    except PaperNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DatabaseError as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/papers/<string:paper_id>", methods=["PUT"])
def update_paper(paper_id):
    """
    Update a paper's metadata.

    Currently supports updating:
    - title
    - authors
    """
    try:
        update_data = {}
        if "title" in request.json:
            update_data["title"] = request.json["title"]
        if "authors" in request.json:
            update_data["authors"] = request.json["authors"]

        if not update_data:
            return jsonify({"error": "No valid fields to update"}), 400

        updated_paper = db.paper_update(paper_id, **update_data)
        return jsonify(updated_paper)
    except PaperNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except InvalidUpdateError as e:
        return jsonify({"error": str(e)}), 400
    except DatabaseError as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/papers/<string:paper_id>", methods=["DELETE"])
def delete_paper(paper_id):
    """
    Delete a paper and all its related resources:
    - Embeddings
    - References
    - S3 file storage
    """
    try:
        db.paper_delete(paper_id)
        return "", 204
    except PaperNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except S3UploadError as e:
        # Even though it's a delete operation, we use S3UploadError for S3 operations
        return jsonify({"error": str(e)}), 503
    except DatabaseError as e:
        return jsonify({"error": str(e)}), 500


@bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors at the blueprint level."""
    return jsonify({"error": "Resource not found"}), 404
