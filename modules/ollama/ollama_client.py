"""
ollama_client.py

This module provides functions for interacting with the Ollama service to generate
embeddings for text and PDF files. It handles sending requests, managing asynchronous
tasks, and handling potential errors.
"""

import os
import time
from typing import List, Optional, Dict
import ollama
import pymupdf
from transformers import AutoTokenizer
from dotenv import load_dotenv
from openai import OpenAI
import httpx
from modules.ollama.pydantic_classes import PaperMetadata
from modules.ollama.pdf_extractor import extract_pdf_content
import instructor

# Force reload of environment variables
load_dotenv(override=True)


# Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


class TokenizerNotAvailableError(Exception):
    """Raised when the required tokenizer is not available or failed to load."""

    pass


class OllamaInitializationError(Exception):
    """Raised when Ollama initialization fails."""

    pass


# --- Configuration ---
# OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")  # Default to localhost if not specified
# logger.info(f"OLLAMA_HOST is set to: {OLLAMA_HOST}")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")  # Default to localhost if not specified
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "mxbai-embed-large")
OLLAMA_USERNAME = os.getenv("OLLAMA_USERNAME", "")
OLLAMA_PASSWORD = os.getenv("OLLAMA_PASSWORD", "")
OLLAMA_API_TIMEOUT = int(os.getenv("OLLAMA_API_TIMEOUT", "60"))
OLLAMA_MAX_RETRIES = int(os.getenv("OLLAMA_MAX_RETRIES", "3"))
OLLAMA_RETRY_DELAY = int(os.getenv("OLLAMA_RETRY_DELAY", "2"))

# Initialize Ollama and tokenizer at module import
TOKENIZER = None
OLLAMA_CLIENT = None


def _initialize_module():
    """Initialize the module's global components"""
    global TOKENIZER, OLLAMA_CLIENT
    try:
        # Initialize tokenizer
        TOKENIZER = AutoTokenizer.from_pretrained("mixedbread-ai/mxbai-embed-large-v1")

        # Initialize Ollama client and pull model
        # logger.info(f"Initializing Ollama client with host: {OLLAMA_HOST}")
        if OLLAMA_USERNAME and OLLAMA_PASSWORD:
            OLLAMA_CLIENT = ollama.Client(host=OLLAMA_HOST, auth=(OLLAMA_USERNAME, OLLAMA_PASSWORD))
            # logger.info("Connected to Ollama with authentication")
        else:
            OLLAMA_CLIENT = ollama.Client(host=OLLAMA_HOST)
            # logger.info("Connected to Ollama without authentication")

        OLLAMA_CLIENT.pull(OLLAMA_EMBEDDING_MODEL)
        # logger.info(f"Successfully pulled Ollama model: {OLLAMA_EMBEDDING_MODEL}")

        # Also pull the chat model
        OLLAMA_CLIENT.pull(OLLAMA_MODEL)
        # logger.info(f"Successfully pulled Ollama model: {OLLAMA_MODEL}")
    except Exception as e:
        # logger.error(f"Failed to initialize module: {e}")
        raise OllamaInitializationError(f"Failed to initialize Ollama: {e}") from e


# Run initialization unless we're in a test environment
if not os.getenv("PYTEST_RUNNING"):
    try:
        _initialize_module()
    except Exception as e:
        # logger.error(f"Module initialization failed: {e}")
        pass

# --- Helper Functions ---


def _send_embed_request_to_ollama(input_text: str, model: str) -> Optional[List[float]]:
    """
    Wrapper for calling the ollama.embed function with retry logic.

    Args:
        input_text (str): The input text for embedding generation.
        model (str): The Ollama model to use.

    Returns:
        Optional[List[float]]: A list of floats representing the embedding,
                               or None if all attempts fail.
    """
    global OLLAMA_CLIENT
    if OLLAMA_CLIENT is None:
        # logger.error("Ollama client not initialized")
        return None

    for attempt in range(OLLAMA_MAX_RETRIES):
        try:
            response = OLLAMA_CLIENT.embeddings(model=model, prompt=input_text)
            if not response or "embedding" not in response:
                raise ValueError(f"Invalid embedding response: {response}")
            return response["embedding"]
        except Exception as e:
            # logger.error(f"Ollama.embed request failed (attempt {attempt + 1}/{OLLAMA_MAX_RETRIES}): {e}")
            if attempt < OLLAMA_MAX_RETRIES - 1:
                time.sleep(OLLAMA_RETRY_DELAY)
    # logger.error(f"Ollama.embed request failed after {OLLAMA_MAX_RETRIES} attempts.")
    return None


# --- Main API Functions ---


def get_paper_embeddings(pdf_path: str) -> Dict[str, List[List[float]]]:
    """
    Gets the embeddings for a given PDF paper. The text is split into segments
    and each segment is embedded separately.

    Returns:
        A dictionary containing:
        - embeddings: List of embeddings (one per text segment)
        - model_name: Name of the embedding model used
        - model_version: Version of the model used
    """
    try:
        text_content = extract_pdf_content(pdf_path)  # extracts & splits content into chunks
        if not text_content:
            # logger.warning(f"No text extracted from PDF: {pdf_path}")
            return {"embeddings": [], "model_name": OLLAMA_EMBEDDING_MODEL, "model_version": "1.0"}

        # Get embeddings for each segment
        embeddings = []
        for chunk in text_content:
            embedding = _send_embed_request_to_ollama(chunk.get("content"), model=OLLAMA_EMBEDDING_MODEL)
            if embedding:
                embeddings.append(embedding)
            else:
                # logger.warning(f"Failed to get embedding for segment in {pdf_path}")
                pass

        return {"embeddings": embeddings, "model_name": OLLAMA_EMBEDDING_MODEL, "model_version": "1.0"}

    except FileNotFoundError:
        raise
    except TokenizerNotAvailableError:
        raise
    except Exception as e:
        # logger.error(f"Error in get_paper_embeddings: {e}")
        raise


def get_query_embeddings(query_string: str) -> Optional[List[float]]:
    """
    Gets the embeddings for a given query string.
    """
    if not query_string.strip():
        # logger.error("Query string cannot be empty.")
        raise ValueError("Query string cannot be empty.")

    embeddings = _send_embed_request_to_ollama(query_string, model=OLLAMA_EMBEDDING_MODEL)
    return embeddings


def get_paper_info(file_path: str) -> dict:  #!TODO: Need to implement this function correctly,
    # for now it returns fake data
    """
    Gets the metadata for a given PDF paper.

    Args:
        file_path: The path to the PDF file.

    Returns:
        A dictionary containing metadata information for the paper.

    Raises:
      FileNotFoundError:  If the file_path does not exist
      Exception:  For any other errors during processing
    """

    logger.info(f"Returning fake metadata for paper: {file_path}")
    return {
        "title": "Sample Academic Paper Title",
        "authors": ["John Doe", "Jane Smith", "Alex Johnson"],
        "field_of_study": "Computer Science",
        "journal": "Journal of AI Research",
        "publication_date": "2025-03-28",
        "doi": "10.1234/sample.5678",
        "keywords": ["artificial intelligence", "machine learning", "neural networks"],
    }

    _initialize_module()  # Ensure Ollama is initialized
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Use PDFDocument from pdfreader module instead of calling pdfreader directly
        # doc = pdfreader.PDFDocument(file_path)
        # first_page = doc.pages[0]
        # text = first_page.extract_text()

        doc = pymupdf.open(file_path)
        if doc.page_count > 0:
            first_page = doc.load_page(0)
            text = first_page.get_text("text")

        # enables `response_model` in create call
        client = instructor.from_openai(
            OpenAI(
                base_url=f"{OLLAMA_HOST.rstrip('/')}/v1",  # Use the OpenAI compatibility endpoint, ensure no double slashes
                api_key="ollama",  # required, but unused
                http_client=httpx.Client(
                    auth=httpx.BasicAuth(username=OLLAMA_USERNAME, password=OLLAMA_PASSWORD) if OLLAMA_USERNAME and OLLAMA_PASSWORD else None,
                    timeout=OLLAMA_API_TIMEOUT,
                ),
            ),
            mode=instructor.Mode.JSON,
        )

        resp = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are a helpful assistant. Extract the metadata from the first page of this academic paper. "
                        "Return only the structured information in JSON format matching the following fields:\n"
                        "- title: The full title of the paper as a string\n"
                        "- authors: A list of author names as a list of strings\n"
                        "- field_of_study: The general research area (e.g., Computer Science, Biology), if identifiable as a string\n"
                        "- journal: The journal name, if available\n"
                        "- publication_date: The publication date in ISO format (YYYY-MM-DD), if found as a date\n"
                        "- doi: The Digital Object Identifier (DOI), if available as a string\n"
                        "- keywords: A list of keywords, if listed as a list of strings\n\n"
                        "Only return fields you can confidently extract from the page — do not guess or fabricate.\n\n"
                        "Here is the first page of the paper:\n\n"
                        f"{text}"
                    ),
                }
            ],
            response_model=PaperMetadata,
        )

        return resp.model_dump()
    except Exception as e:
        # logger.error(f"Error generating paper info for {file_path}: {e}")
        raise e
