"""
ollama.py

This module provides functions for interacting with the Ollama service to generate
embeddings for text and PDF files. It handles sending requests, managing asynchronous
tasks, and handling potential errors.
"""

import os
import requests
import json
import time
import logging
from typing import List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Configuration ---
#  Load these from environment variables or a configuration file.  Using
#  environment variables is generally preferred for security and flexibility.

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")  # Default Ollama host
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistralai/Mistral-7B-Instruct-v0.1")  # Default model
OLLAMA_API_TIMEOUT = int(os.getenv("OLLAMA_API_TIMEOUT", "60"))  # Timeout in seconds, default 60
OLLAMA_MAX_RETRIES = int(os.getenv("OLLAMA_MAX_RETRIES", "3"))  # Max retries, default 3
OLLAMA_RETRY_DELAY = int(os.getenv("OLLAMA_RETRY_DELAY", "2"))  # Retry delay in seconds, default 2

# --- Helper Functions ---


def _send_request_to_ollama(prompt: str, model: str = OLLAMA_MODEL, stream: bool = False) -> Optional[List[float]]:
    """
    Sends a request to the Ollama API and handles responses, including errors and streaming.

    Args:
        prompt: The input text for embedding generation.
        model: The Ollama model to use (defaults to OLLAMA_MODEL).
        stream:  Whether to use streaming (not used for embeddings, but useful for completion).

    Returns:
        A list of floats representing the embedding, or None if an error occurred.

    Raises:
        requests.exceptions.RequestException: For network-related errors.
        ValueError:  For invalid JSON responses or other data issues.
    """
    url = f"{OLLAMA_HOST}/api/embeddings"
    headers = {"Content-Type": "application/json"}
    data = {
        "prompt": prompt,
        "model": model,
        "stream": stream,  # Include stream, even if we don't use it
        "options": {},  # Add any model-specific options here.
    }

    for attempt in range(OLLAMA_MAX_RETRIES):
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data), timeout=OLLAMA_API_TIMEOUT)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

            # Assuming the Ollama embeddings API returns JSON like: {"embedding": [...]}
            response_json = response.json()
            if "embedding" not in response_json:
                raise ValueError(f"Invalid response from Ollama: {response_json}")

            return response_json["embedding"]

        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API request failed (attempt {attempt + 1}/{OLLAMA_MAX_RETRIES}): {e}")
            if attempt < OLLAMA_MAX_RETRIES - 1:
                time.sleep(OLLAMA_RETRY_DELAY)
        except ValueError as e:
            logger.error(f"Error parsing Ollama response (attempt {attempt + 1}/{OLLAMA_MAX_RETRIES}): {e}")
            if attempt < OLLAMA_MAX_RETRIES - 1:
                time.sleep(OLLAMA_RETRY_DELAY)

    # If all retries fail, return None
    logger.error(f"Ollama API request failed after {OLLAMA_MAX_RETRIES} attempts.")
    return None


def _extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts text content from a PDF file.  Uses a robust library like
    PyMuPDF (fitz) for better accuracy and handling of various PDF formats.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        The extracted text as a single string.

    Raises:
        FileNotFoundError: If the PDF file does not exist.
        Exception:  For other PDF parsing errors.
    """
    try:
        import fitz  # PyMuPDF

        with fitz.open(pdf_path) as doc:
            text = ""
            for page in doc:
                text += page.get_text()
            return text
    except FileNotFoundError:
        logger.error(f"PDF file not found: {pdf_path}")
        raise
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        raise


# --- Main API Functions ---


def get_paper_embeddings(pdf_path: str) -> Optional[List[float]]:
    """
    Gets the embeddings for a given PDF paper.

    Args:
        pdf_path: The path to the PDF file.

    Returns:
        A list of floats representing the embedding, or None if an error occurred.

    Raises:
      FileNotFoundError:  If the pdf_path does not exist
      Exception:  For other errors related to PDF processing or Ollama communication.
    """
    try:
        text_content = _extract_text_from_pdf(pdf_path)
        if not text_content:
            logger.warning(f"No text extracted from PDF: {pdf_path}")
            return None

        #TODO: needs to be implemented
        raise NotImplementedError("get_paper_embeddings is not implemented yet.")
        #return embeddings

    except FileNotFoundError:
        raise  # Re-raise to be handled by caller
    except Exception as e:
        logger.error(f"Error in get_paper_embeddings: {e}")
        raise  # Re-raise general exception


def get_query_embeddings(query_string: str) -> Optional[List[float]]:
    """
    Gets the embeddings for a given query string.

    Args:
        query_string: The input text string.

    Returns:
        A list of floats representing the embedding, or None if an error occurred.

    Raises:
      ValueError: If query string is empty
      Exception:  For any other errors during communication with Ollama
    """
    if not query_string.strip():
        logger.error("Query string cannot be empty.")
        raise ValueError("Query string cannot be empty.")
    raise NotImplementedError("get_query_embeddings is not implemented yet.")
    embeddings = _send_request_to_ollama(query_string)
    return embeddings