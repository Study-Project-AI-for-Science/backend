from flask import Blueprint, request, jsonify
from flask_cors import CORS
import os
import tempfile
from modules.database import database as db
from modules.database.database import (
    PaperNotFoundError,
    FileHashError,
    DatabaseError,
    EmbeddingNotFoundError,
    InvalidUpdateError,
    DuplicatePaperError,
)
from modules.latex_parser import reference_parser
from modules.storage.storage import S3UploadError
from modules.ollama import ollama_client
from modules.retriever.arxiv import arxiv_retriever

bp = Blueprint("main", __name__)
CORS(bp)  # Enable CORS for all routes in this blueprint


@bp.route("/")
def home():
    return jsonify({"message": "API is running"})


@bp.route("/papers", methods=["POST"])
def create_paper():
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
            title: str = paper_metadata.get("title", title)
            authors: str = paper_metadata.get("authors", authors)
            abstract: str = paper_metadata.get("abstract", "")
            paper_url: str = paper_metadata.get("url", "")
            published: str = paper_metadata.get("published_date", "")
            updated: str = paper_metadata.get("updated_date", "")

            # Insert the paper into the database
            paper_id = db.paper_insert(temp_file.name, title, authors, abstract, paper_url, published, updated)
            # Clean up the temporary file
            os.unlink(temp_file.name)

            # TODO: Ensure paper_id exists @tim
            arxiv_paper_id = paper_metadata.paper_id

            # Extract paper references @tim
            references = reference_parser.extract_references(arxiv_paper_id) 

            # Insert references into database
            db.paper_references_insert_many(paper_id, references)

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
    try:
        references = db.paper_references_list(paper_id)
        return jsonify(references)
    except DatabaseError as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/papers", methods=["GET"])
def list_papers():
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
    try:
        paper = db.paper_find(paper_id)
        # Remove the embedding from the response to reduce payload size
        if "embedding" in paper:
            del paper["embedding"]
        return jsonify(paper)
    except PaperNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DatabaseError as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/papers/<string:paper_id>", methods=["PUT"])
def update_paper(paper_id):
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
    return jsonify({"error": "Resource not found"}), 404
