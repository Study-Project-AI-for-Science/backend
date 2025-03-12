import logging
import tarfile
from typing import Generator, Optional, List
import arxiv
import re
import pymupdf
import os

# Set up logging
logger = logging.getLogger(__name__)

# Initialize global client
client = arxiv.Client()


class ArxivRetrievalError(Exception):
    """Base exception for arxiv retrieval errors."""

    pass


class ArxivPaperNotFoundError(ArxivRetrievalError):
    """Raised when a paper cannot be found on arxiv."""

    pass


class ArxivDownloadError(ArxivRetrievalError):
    """Raised when there's an error downloading a paper from arxiv."""

    pass


class PDFExtractionError(Exception):
    """Raised when there's an error extracting information from a PDF file."""

    pass

class ExtractionError(Exception):
    """Raised when there's an error extracting a tar.gz file."""
    pass

def extract_tar_gz(file_path: str, output_dir: str) -> str:
    """
    Extract a tar.gz file to a directory.

    Args:
        file_path (str): Path to the tar.gz file.
        output_dir (str): Directory where the contents should be extracted.

    Returns:
        str: Path to the extracted directory.
    """
    logger.debug(f"Extracting {file_path} to {output_dir}")
    try:
        with tarfile.open(file_path, "r:gz") as tar:
            tar.extractall(output_dir)
            logger.info(f"Successfully extracted {file_path} to {output_dir}")
            return output_dir
    except Exception as e:
        logger.error(f"Error extracting {file_path}: {str(e)}")
        raise ExtractionError(f"Error extracting {file_path}: {str(e)}") from e

def _search_arxiv_id(arxiv_id: str) -> Optional[arxiv.Result]:
    """
    Search for a paper on arXiv using its ID.

    Args:
        arxiv_id (str): The arXiv ID of the paper.

    Returns:
        Optional[arxiv.Result]: The paper result if found, None otherwise.

    Raises:
        ArxivRetrievalError: If there's an error querying the arXiv API.
    """
    logger.debug(f"Searching for paper with arXiv ID: {arxiv_id}")
    try:
        search = arxiv.Search(id_list=[arxiv_id])
        results = client.results(search)
        result = next(results, None)
        if result:
            logger.info(f"Found paper with arXiv ID: {arxiv_id}")
        else:
            logger.warning(f"No paper found with arXiv ID: {arxiv_id}")
        return result
    except Exception as e:
        logger.error(f"Error searching arXiv ID {arxiv_id}: {str(e)}")
        raise ArxivRetrievalError(f"Error searching arXiv ID {arxiv_id}: {str(e)}") from e


def _search_arxiv_metadata(authors: str, title: str) -> Optional[arxiv.Result]:
    # This actually doesn't really work well
    """
    Search for a paper on arXiv using author and title information.

    Args:
        authors (str): Author names to search for.
        title (str): Paper title to search for.

    Returns:
        Optional[arxiv.Result]: The paper result if found, None otherwise.

    Raises:
        ArxivRetrievalError: If there's an error querying the arXiv API.
    """
    logger.debug(f"Searching for paper with title: {title} and authors: {authors}")
    try:
        filters = []
        if authors:
            filters.append(f"au:{authors}")
        if title:
            filters.append(f"ti:{title}")
        query = " AND ".join(filters)
        search = arxiv.Search(
            query=query, max_results=1, sort_by=arxiv.SortCriterion.Relevance, sort_order=arxiv.SortOrder.Descending
        )
        results = client.results(search)
        result = next(results, None)
        if result:
            logger.info("Found paper matching metadata search")
        else:
            logger.warning("No paper found matching metadata search")
        return result
    except Exception as e:
        logger.error(f"Error searching arXiv with metadata: {str(e)}")
        raise ArxivRetrievalError(f"Error searching arXiv with metadata: {str(e)}") from e


def _search_arxiv_all(query: str, max_results: int) -> Generator[arxiv.Result, None, None]:
    """
    Search for papers on arXiv using a general query.

    Args:
        query (str): The search query.
        max_results (int): Maximum number of results to return.

    Returns:
        Generator[arxiv.Result, None, None]: Generator of paper results.

    Raises:
        ArxivRetrievalError: If there's an error querying the arXiv API.
    """
    logger.debug(f"Performing general search with query: {query}, max_results: {max_results}")
    try:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
            sort_order=arxiv.SortOrder.Descending,
        )
        return client.results(search)
    except Exception as e:
        logger.error(f"Error searching arXiv with query '{query}': {str(e)}")
        raise ArxivRetrievalError(f"Error searching arXiv with query '{query}': {str(e)}") from e


def _download_arxiv_id(arxiv_id: str, output_dir: str) -> Optional[str]:
    """
    Download a paper from arXiv using its ID.

    Args:
        arxiv_id (str): The arXiv ID of the paper.
        output_dir (str): Directory where the paper should be downloaded.

    Returns:
        Optional[str]: Path to the downloaded paper if successful, None otherwise.

    Raises:
        ArxivPaperNotFoundError: If the paper cannot be found.
        ArxivDownloadError: If there's an error downloading the paper.
    """
    logger.debug(f"Attempting to download paper with ID {arxiv_id} to {output_dir}")
    paper = _search_arxiv_id(arxiv_id)
    if not paper:
        logger.error(f"Paper with ID {arxiv_id} not found")
        raise ArxivPaperNotFoundError(f"Paper with ID {arxiv_id} not found")
    return _download_arxiv_paper(paper, output_dir)


def _download_arxiv_paper(paper: arxiv.Result, output_dir: str) -> str:
    """
    Download a paper from arXiv using its Result object.

    Args:
        paper (arxiv.Result): The paper result object.
        output_dir (str): Directory where the paper should be downloaded.

    Returns:
        str: Path to the downloaded paper.

    Raises:
        ArxivDownloadError: If there's an error downloading the paper.
    """
    logger.debug(f"Attempting to download paper {paper.title} to {output_dir}")
    try:
        path = paper.download_pdf(output_dir)
        paper.download_source(output_dir)
        tar_gz_path = path[:-4] + ".tar.gz"
        if os.path.exists(tar_gz_path):
            try:
                extract_tar_gz(path[:-4] + ".tar.gz", output_dir + "/" + path.split("/")[-1][:-4])
                os.remove(tar_gz_path)
                logger.info(f"Deleted archive file {tar_gz_path}")
            except Exception as e:
                logger.warning(f"Failed to delete archive file: {str(e)}")
        logger.info(f"Successfully downloaded paper {paper.get_short_id()} to {path}")
        return path
    except Exception as e:
        logger.error(f"Error downloading paper {paper.get_short_id()}: {str(e)}")
        raise ArxivDownloadError(f"Error downloading paper {paper.get_short_id()}: {str(e)}") from e


def _get_metadata_arxiv_paper(paper: arxiv.Result) -> dict:
    """
    Extract metadata from an arXiv paper result.

    Args:
        paper (arxiv.Result): The paper result object.

    Returns:
        dict: Dictionary containing paper metadata including title, authors,
              abstract, URL, arXiv ID, and dates.
    """
    authors = ", ".join(author.name for author in paper.authors)

    return {
        "title": paper.title,
        "authors": authors,
        "abstract": paper.summary,
        "url": paper.entry_id,
        "arxiv_id": paper.get_short_id(),
        "published_date": paper.published,
        "updated_date": paper.updated,
    }


# MAIN FUNCTIONS


def extract_arxiv_ids(text: str) -> List[str]:
    """
    Extract all arXiv IDs from the input text.

    Args:
        text (str): Input string that may contain one or more arXiv IDs.

    Returns:
        List[str]: A list of extracted arXiv IDs.
    """
    pattern = r"\d{4}\.\d{5}"
    return re.findall(pattern, text)


def paper_get_metadata(file_path: str) -> Optional[dict]:
    # TODO add option that gives first page for title/metadata parsing to LLM and afterward try to retrieve from arxiv
    """
    Extract metadata from a PDF file, attempting multiple methods:
    1. Look for arXiv ID in filename
    2. Search using filename as title
    3. Extract arXiv ID from first page of PDF

    Args:
        file_path (str): Path to the PDF file.

    Returns:
        Optional[dict]: Dictionary containing paper metadata if found, empty dict if not found.

    Raises:
        ArxivRetrievalError: If there's an error querying the arXiv API.
    """
    logger.debug(f"Attempting to extract metadata from {file_path}")

    # Try to find arxiv ID in filename
    arxiv_ids = extract_arxiv_ids(file_path)
    if arxiv_ids:
        logger.debug(f"Found arXiv ID in filename: {arxiv_ids[0]}")
        try:
            paper = _search_arxiv_id(arxiv_ids[0])
            if paper:
                logger.info("Successfully retrieved metadata using arXiv ID from filename")
                return _get_metadata_arxiv_paper(paper)
        except ArxivRetrievalError:
            logger.warning("Failed to retrieve metadata using arXiv ID from filename")
            pass

    # Try to find paper using filename
    logger.debug("Attempting to find paper using filename")
    try:
        results = _search_arxiv_all(file_path[:-4], 15)
        for paper in results:
            if paper.title in file_path:
                logger.info("Successfully retrieved metadata using filename search")
                return _get_metadata_arxiv_paper(paper)
    except ArxivRetrievalError:
        logger.warning("Failed to retrieve metadata using filename search")
        pass

    # Try to find arxiv ID in PDF content
    logger.debug("Attempting to find arXiv ID in PDF content")
    try:
        doc = pymupdf.open(file_path)
        if doc.page_count > 0:
            first_page = doc.load_page(0)
            text = first_page.get_text("text")
            arxiv_ids_from_text = extract_arxiv_ids(text)
            if arxiv_ids_from_text:
                logger.debug(f"Found arXiv ID in PDF content: {arxiv_ids_from_text[0]}")
                try:
                    paper = _search_arxiv_id(arxiv_ids_from_text[0])
                    if paper:
                        logger.info("Successfully retrieved metadata using arXiv ID from PDF content")
                        return _get_metadata_arxiv_paper(paper)
                except ArxivRetrievalError:
                    logger.warning("Failed to retrieve metadata using arXiv ID from PDF content")
                    pass
    except Exception as e:
        error_msg = f"Error extracting information from PDF {file_path}: {str(e)}"
        logger.error(error_msg)
        # Return empty dict instead of raising an exception
        # This will allow the system to continue with default values

    logger.warning(f"Could not extract metadata from {file_path}")
    return {}


def paper_download_arxiv_id(arxiv_id: str, output_dir: str) -> str:
    """
    Download a paper from arXiv using its ID.

    Args:
        arxiv_id (str): The arXiv ID of the paper.
        output_dir (str): Directory where the paper should be downloaded.

    Returns:
        str: Path to the downloaded paper.

    Raises:
        ArxivPaperNotFoundError: If the paper cannot be found.
        ArxivDownloadError: If there's an error downloading the paper.
    """
    logger.debug(f"Attempting to download paper with ID {arxiv_id} to {output_dir}")
    paper_path = _download_arxiv_id(arxiv_id, output_dir)
    if not paper_path:
        logger.error(f"Paper with ID {arxiv_id} not found")
        raise ArxivPaperNotFoundError(f"Paper with ID {arxiv_id} not found")
    logger.info(f"Successfully downloaded paper {arxiv_id} to {paper_path}")
    return paper_path


def paper_download_arxiv_metadata(authors: str = "", title: str = "", output_dir: str = ".") -> str:
    """
    Download a paper from arXiv using author and title information.

    Args:
        authors (str): Author names in format "author1, author2, author3".
        title (str): Paper title.
        output_dir (str): Directory where the paper should be downloaded.

    Returns:
        str: Path to the downloaded paper.

    Raises:
        ArxivPaperNotFoundError: If the paper cannot be found.
        ArxivDownloadError: If there's an error downloading the paper.
    """
    logger.debug(f"Attempting to download paper with title '{title}' by {authors}")
    title = title.replace(":", "\\:")
    title = title.replace("-", "\\-")
    paper = _search_arxiv_metadata(authors, title)
    if not paper:
        error_msg = f"Paper with title '{title}' by {authors} not found"
        logger.error(error_msg)
        raise ArxivPaperNotFoundError(error_msg)

    paper_path = _download_arxiv_paper(paper, output_dir)
    if not paper_path:
        error_msg = f"Error downloading paper with title '{title}'"
        logger.error(error_msg)
        raise ArxivDownloadError(error_msg)

    logger.info(f"Successfully downloaded paper to {paper_path}")
    return paper_path
