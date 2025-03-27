"""
ollama_client.py

This module provides functions for interacting with the Ollama service to generate
embeddings for text and PDF files. It handles sending requests, managing asynchronous
tasks, and handling potential errors.
"""

import os
import time
import logging
from typing import List, Optional, Dict
import pymupdf
import ollama
from transformers import AutoTokenizer
from dotenv import load_dotenv
import pdfreader
import OpenAI
from modules.ollama.pydantic_classes import PaperMetadata
import instructor

# Force reload of environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TokenizerNotAvailableError(Exception):
    """Raised when the required tokenizer is not available or failed to load."""

    pass


class OllamaInitializationError(Exception):
    """Raised when Ollama initialization fails."""

    pass


# --- Configuration ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")  # Default to localhost if not specified
logger.info(f"OLLAMA_HOST is set to: {OLLAMA_HOST}")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistralai/Mistral-7B-Instruct-v0.1")
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
        logger.info(f"Initializing Ollama client with host: {OLLAMA_HOST}")
        if OLLAMA_USERNAME and OLLAMA_PASSWORD:
            OLLAMA_CLIENT = ollama.Client(host=OLLAMA_HOST, auth=(OLLAMA_USERNAME, OLLAMA_PASSWORD))
            logger.info("Connected to Ollama with authentication")
        else:
            OLLAMA_CLIENT = ollama.Client(host=OLLAMA_HOST)
            logger.info("Connected to Ollama without authentication")

        OLLAMA_CLIENT.pull(OLLAMA_EMBEDDING_MODEL)
        logger.info(f"Successfully pulled Ollama model: {OLLAMA_EMBEDDING_MODEL}")
    except Exception as e:
        logger.error(f"Failed to initialize module: {e}")
        raise OllamaInitializationError(f"Failed to initialize Ollama: {e}") from e


# Run initialization unless we're in a test environment
if not os.getenv("PYTEST_RUNNING"):
    try:
        _initialize_module()
    except Exception as e:
        logger.error(f"Module initialization failed: {e}")

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
        logger.error("Ollama client not initialized")
        return None

    for attempt in range(OLLAMA_MAX_RETRIES):
        try:
            response = OLLAMA_CLIENT.embeddings(model=model, prompt=input_text)
            if not response or "embedding" not in response:
                raise ValueError(f"Invalid embedding response: {response}")
            return response["embedding"]
        except Exception as e:
            logger.error(f"Ollama.embed request failed (attempt {attempt + 1}/{OLLAMA_MAX_RETRIES}): {e}")
            if attempt < OLLAMA_MAX_RETRIES - 1:
                time.sleep(OLLAMA_RETRY_DELAY)
    logger.error(f"Ollama.embed request failed after {OLLAMA_MAX_RETRIES} attempts.")
    return None


def _extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts text content from a PDF file using PyMuPDF for better accuracy
    and handling of various PDF formats.
    """
    try:
        with pymupdf.open(pdf_path) as doc:
            text = ""
            for page in doc:
                text += page.get_text()
            return text
    except pymupdf.FileNotFoundError as err:
        logger.error(f"PDF file not found: {pdf_path}")
        raise FileNotFoundError(f"File not found: {pdf_path}") from err
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        raise


def _split_text_into_segments(text: str, max_tokens: int = 512) -> List[str]:
    """
    Splits text into segments of approximately max_tokens tokens.
    Uses a tokenizer to properly count tokens and split text appropriately.
    """
    if not TOKENIZER:
        raise TokenizerNotAvailableError(
            model_name="mixedbread-ai/mxbai-embed-large-v1",
            detail="Tokenizer failed to initialize during module startup",
        )

    # Split initial text into paragraphs to maintain some structure
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    segments = []
    current_segment = ""
    current_tokens = []

    for para in paragraphs:
        # Tokenize the paragraph
        para_tokens = TOKENIZER.encode(para, add_special_tokens=False, return_tensors="np")[0].tolist()

        # If single paragraph is longer than max_tokens, split it
        if len(para_tokens) > max_tokens:
            # First add any existing segment
            if current_tokens:
                segments.append(current_segment.strip())
                current_segment = ""
                current_tokens = []

            # Split long paragraph into smaller chunks
            words = para.split()
            # TODO: maybe sentence tokenizer
            current_chunk = []
            for word in words:
                word_tokens = TOKENIZER.encode(word + " ", add_special_tokens=False)
                if len(current_tokens) + len(word_tokens) <= max_tokens:
                    current_tokens.extend(word_tokens.tolist())
                    current_chunk.append(word)
                else:
                    segments.append(" ".join(current_chunk))
                    current_chunk = [word]
                    current_tokens = word_tokens.tolist()

            if current_chunk:
                segments.append(" ".join(current_chunk))
                current_tokens = []
                current_segment = ""

        # For normal-sized paragraphs
        else:
            if len(current_tokens) + len(para_tokens) <= max_tokens:
                current_segment += para + " "
                current_tokens.extend(para_tokens)
            else:
                segments.append(current_segment.strip())
                current_segment = para + " "
                current_tokens = para_tokens

    if current_segment:
        segments.append(current_segment.strip())

    return segments


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
        text_content = _extract_text_from_pdf(pdf_path)
        if not text_content:
            logger.warning(f"No text extracted from PDF: {pdf_path}")
            return {"embeddings": [], "model_name": OLLAMA_EMBEDDING_MODEL, "model_version": "1.0"}

        # Split text into segments
        try:
            text_segments = _split_text_into_segments(text_content)
        except TokenizerNotAvailableError as e:
            logger.error(f"Failed to segment text: {e}")
            raise

        # Get embeddings for each segment
        embeddings = []
        for segment in text_segments:
            embedding = _send_embed_request_to_ollama(segment, model=OLLAMA_EMBEDDING_MODEL)
            if embedding:
                embeddings.append(embedding)
            else:
                logger.warning(f"Failed to get embedding for segment in {pdf_path}")

        return {"embeddings": embeddings, "model_name": OLLAMA_EMBEDDING_MODEL, "model_version": "1.0"}

    except FileNotFoundError:
        raise
    except TokenizerNotAvailableError:
        raise
    except Exception as e:
        logger.error(f"Error in get_paper_embeddings: {e}")
        raise


def get_query_embeddings(query_string: str) -> Optional[List[float]]:
    """
    Gets the embeddings for a given query string.
    """
    if not query_string.strip():
        logger.error("Query string cannot be empty.")
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
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        reader = pdfreader(file_path)
        first_page = reader.pages[0]
        text = first_page.extract_text()
            
        # enables `response_model` in create call
        client = instructor.from_openai(
            OpenAI(
                base_url="http://localhost:11434",
                api_key="ollama",  # required, but unused
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
        logger.error(f"Error generating paper info for {file_path}: {e}")
        raise e
