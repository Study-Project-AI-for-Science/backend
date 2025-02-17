"""
storage.py

This module provides a wrapper for S3/MinIO storage operations, handling file uploads,
downloads, and related operations with proper error handling and retrying mechanisms.
"""

import os
import time
import logging
import boto3
import botocore.exceptions
from dotenv import load_dotenv
from uuid_extensions import uuid7str as uuid7

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MinIO configuration
MINIO_URL = os.getenv("MINIO_URL", "http://localhost:9000")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "ROOT_USER")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "TOOR_PASSWORD")
BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "papers")

# Initialize the MinIO client using boto3
s3_client = boto3.client(
    "s3",
    endpoint_url=MINIO_URL,
    aws_access_key_id=MINIO_ROOT_USER,
    aws_secret_access_key=MINIO_ROOT_PASSWORD,
)


class S3UploadError(Exception):
    """Exception raised when uploading a file to S3 fails."""

    pass


class S3DownloadError(Exception):
    """Exception raised when downloading a file from S3 fails."""

    pass


def upload_file(file_path: str) -> str:
    """
    Uploads a file to S3 with error handling and retry mechanism.

    Description:
        Uploads the file located at `file_path` to the S3 storage and returns its URL.

    Parameters:
        file_path (str): The local filesystem path of the file to upload.

    Returns:
        str: The URL of the uploaded file on S3.

    Raises:
        S3UploadError: If the upload fails after the maximum number of retries.

    Example:
        url = upload_file("/path/to/file.pdf")
    """
    file_id = str(uuid7())
    file_name = os.path.basename(file_path)
    object_name = f"{file_id}/{file_name}"
    max_retries = 3
    delay = 2  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            s3_client.upload_file(file_path, BUCKET_NAME, object_name)
            url = f"{MINIO_URL}/{BUCKET_NAME}/{object_name}"
            logger.info(f"Successfully uploaded file to S3: {url}")
            return url
        except (botocore.exceptions.ClientError, botocore.exceptions.EndpointConnectionError) as e:
            logger.error(f"S3 error on attempt {attempt} for file {file_path}: {e}")
            if attempt >= max_retries:
                raise S3UploadError(f"Failed to upload {file_path} to S3 after {max_retries} attempts: {str(e)}") from e
        time.sleep(delay)


def download_file(file_url: str, destination_path: str) -> None:
    """
    Downloads a file from S3 and saves it to a local destination.

    Description:
        Given a file URL from S3, this function extracts the S3 object key and downloads
        the file to the provided destination path.

    Parameters:
        file_url (str): The complete URL of the file stored on S3.
        destination_path (str): The local filesystem path where the file should be saved.

    Returns:
        None

    Raises:
        ValueError: If the `file_url` is not valid.
        S3DownloadError: If there is an error during the file download.

    Example:
        download_file("http://localhost:9000/papers/abc/filename.pdf", "/local/path/file.pdf")
    """
    prefix = f"{MINIO_URL}/{BUCKET_NAME}/"
    if not file_url.startswith(prefix):
        logger.error(f"Invalid file URL: {file_url}")
        raise ValueError(f"Invalid file URL: {file_url}")
    object_name = file_url[len(prefix) :]

    try:
        s3_client.download_file(BUCKET_NAME, object_name, destination_path)
        logger.info(f"Successfully downloaded file from S3 to {destination_path}")
    except botocore.exceptions.ClientError as e:
        logger.error(f"Error downloading file from S3: {e}")
        raise S3DownloadError(f"Failed to download file from S3: {str(e)}") from e


def delete_file(file_url: str) -> None:
    """
    Deletes a file from S3 storage.

    Description:
        Given a file URL from S3, this function extracts the S3 object key and deletes
        the corresponding file from storage.

    Parameters:
        file_url (str): The complete URL of the file stored on S3.

    Returns:
        None

    Raises:
        ValueError: If the `file_url` is not valid.
        S3UploadError: If there is an error during the file deletion.

    Example:
        delete_file("http://localhost:9000/papers/abc/filename.pdf")
    """
    prefix = f"{MINIO_URL}/{BUCKET_NAME}/"
    if not file_url.startswith(prefix):
        logger.error(f"Invalid file URL: {file_url}")
        raise ValueError(f"Invalid file URL: {file_url}")

    object_name = file_url[len(prefix) :]
    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=object_name)
        logger.info(f"Successfully deleted file from S3: {file_url}")
    except botocore.exceptions.ClientError as e:
        logger.error(f"Error deleting file from S3: {e}")
        raise S3UploadError(f"Failed to delete file from S3: {str(e)}") from e
