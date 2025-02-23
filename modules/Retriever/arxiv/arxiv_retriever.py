from typing import Generator, Optional, List
import arxiv
import re
import pymupdf


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
    try:
        results = arxiv.query(id_list=[arxiv_id])
        return next(results, None)
    except Exception as e:
        raise ArxivRetrievalError(f"Error searching arXiv ID {arxiv_id}: {str(e)}") from e


def _search_arxiv_metadata(authors: str, title: str) -> Optional[arxiv.Result]:
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
    try:
        filters = []
        if authors:
            filters.append(f"au:{authors}")
        if title:
            filters.append(f"ti:{title}")
        query = " AND ".join(filters)
        results = arxiv.query(query=query)
        return next(results, None)
    except Exception as e:
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
    try:
        return arxiv.query(query=query, max_results=max_results)
    except Exception as e:
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
    paper = _search_arxiv_id(arxiv_id)
    if not paper:
        raise ArxivPaperNotFoundError(f"Paper with ID {arxiv_id} not found")
    try:
        return paper.download_pdf(output_dir)
    except Exception as e:
        raise ArxivDownloadError(f"Error downloading paper {arxiv_id}: {str(e)}") from e


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
    try:
        return paper.download_pdf(output_dir)
    except Exception as e:
        raise ArxivDownloadError(f"Error downloading paper: {str(e)}") from e


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
    """
    Extract metadata from a PDF file, attempting multiple methods:
    1. Look for arXiv ID in filename
    2. Search using filename as title
    3. Extract arXiv ID from first page of PDF

    Args:
        file_path (str): Path to the PDF file.

    Returns:
        Optional[dict]: Dictionary containing paper metadata if found, None otherwise.

    Raises:
        PDFExtractionError: If there's an error processing the PDF file.
        ArxivRetrievalError: If there's an error querying the arXiv API.
    """
    # Try to find arxiv ID in filename
    arxiv_ids = extract_arxiv_ids(file_path)
    if arxiv_ids:
        try:
            paper = _search_arxiv_id(arxiv_ids[0])
            if paper:
                return _get_metadata_arxiv_paper(paper)
        except ArxivRetrievalError:
            pass  # Continue with other methods if this fails

    # Try to find paper using filename
    try:
        results = _search_arxiv_all(file_path[:-4], 15)
        for paper in results:
            if paper.title in file_path:
                return _get_metadata_arxiv_paper(paper)
    except ArxivRetrievalError:
        pass  # Continue with other methods if this fails

    # Try to find arxiv ID in PDF content
    try:
        doc = pymupdf.open(file_path)
        if doc.page_count > 0:
            first_page = doc.load_page(0)
            text = first_page.get_text("text")
            arxiv_ids_from_text = extract_arxiv_ids(text)
            if arxiv_ids_from_text:
                try:
                    paper = _search_arxiv_id(arxiv_ids_from_text[0])
                    if paper:
                        return _get_metadata_arxiv_paper(paper)
                except ArxivRetrievalError:
                    pass
    except Exception as e:
        raise PDFExtractionError(f"Error extracting information from PDF {file_path}: {str(e)}") from e

    return None


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
    paper_path = _download_arxiv_id(arxiv_id, output_dir)
    if not paper_path:
        raise ArxivPaperNotFoundError(f"Paper with ID {arxiv_id} not found")
    return paper_path


def paper_download_arxiv_metadata(authors: str, title: str, output_dir: str) -> str:
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
    title = title.replace(":", "\\:")
    paper = _search_arxiv_metadata(authors, title)
    if not paper:
        raise ArxivPaperNotFoundError(f"Paper with title '{title}' by {authors} not found")

    paper_path = _download_arxiv_paper(paper, output_dir)
    if not paper_path:
        raise ArxivDownloadError(f"Error downloading paper with title '{title}'")
    return paper_path
