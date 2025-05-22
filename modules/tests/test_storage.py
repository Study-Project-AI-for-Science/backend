import os
import pytest
import botocore.exceptions
from unittest.mock import patch
from modules.storage.storage import (
    upload_file,
    download_file,
    delete_file,
    S3UploadError,
    S3DownloadError,
)

# Test data
TEST_FILE_PATH = "test.pdf"
TEST_FILE_URL = "http://localhost:9000/papers/123/test.pdf"
TEST_BUCKET = "papers"


@pytest.fixture
def mock_s3_client():
    with patch("modules.storage.storage.s3_client") as mock_client:
        yield mock_client


@pytest.fixture
def test_file():
    """Create and clean up a test file"""
    with open(TEST_FILE_PATH, "wb") as f:
        f.write(b"test content")
    yield TEST_FILE_PATH
    if os.path.exists(TEST_FILE_PATH):
        os.remove(TEST_FILE_PATH)


def test_upload_file_success(mock_s3_client, test_file):
    """Test successful file upload"""
    url = upload_file(test_file)

    mock_s3_client.upload_file.assert_called_once()
    assert url.startswith("http://localhost:9000/papers/")
    assert url.endswith("/test.pdf")


def test_upload_file_error(mock_s3_client, test_file):
    """Test file upload with S3 error"""
    mock_s3_client.upload_file.side_effect = botocore.exceptions.ClientError(
        error_response={"Error": {"Code": "500", "Message": "S3 error"}}, operation_name="upload_file"
    )

    with pytest.raises(S3UploadError):
        upload_file(test_file)


def test_download_file_success(mock_s3_client):
    """Test successful file download"""
    destination = "downloaded_test.pdf"
    try:
        download_file(TEST_FILE_URL, destination)

        mock_s3_client.download_file.assert_called_once_with(TEST_BUCKET, "123/test.pdf", destination)
    finally:
        if os.path.exists(destination):
            os.remove(destination)


def test_download_file_invalid_url():
    """Test download with invalid URL"""
    with pytest.raises(ValueError):
        download_file("invalid_url", "destination.pdf")


def test_download_file_error(mock_s3_client):
    """Test file download with S3 error"""
    mock_s3_client.download_file.side_effect = botocore.exceptions.ClientError(
        error_response={"Error": {"Code": "500", "Message": "S3 error"}}, operation_name="download_file"
    )

    with pytest.raises(S3DownloadError):
        download_file(TEST_FILE_URL, "destination.pdf")


def test_delete_file_success(mock_s3_client):
    """Test successful file deletion"""
    delete_file(TEST_FILE_URL)

    mock_s3_client.delete_object.assert_called_once_with(Bucket=TEST_BUCKET, Key="123/test.pdf")


def test_delete_file_invalid_url():
    """Test deletion with invalid URL"""
    with pytest.raises(ValueError):
        delete_file("invalid_url")


def test_delete_file_error(mock_s3_client):
    """Test file deletion with S3 error"""
    mock_s3_client.delete_object.side_effect = botocore.exceptions.ClientError(
        error_response={"Error": {"Code": "500", "Message": "S3 error"}}, operation_name="delete_object"
    )

    with pytest.raises(S3UploadError):
        delete_file(TEST_FILE_URL)
