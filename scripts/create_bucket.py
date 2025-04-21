import boto3
from botocore.exceptions import ClientError
import os


def create_bucket(s3_url, s3_access_key, s3_secret_key, bucket_name):
    """
    Create a bucket on the MinIO server using the AWS S3 API.
    """
    # Initialize S3 client
    s3_client = boto3.client(
        "s3",
        endpoint_url=s3_url,
        aws_access_key_id=s3_access_key,
        aws_secret_access_key=s3_secret_key,
    )

    try:
        # Check if the bucket already exists
        response = s3_client.list_buckets()
        for bucket in response.get("Buckets", []):
            if bucket["Name"] == bucket_name:
                print(f"Bucket '{bucket_name}' already exists.")
                return

        # Create the bucket
        s3_client.create_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' created successfully!")
    except ClientError as e:
        print(f"Error creating bucket: {e}")


if __name__ == "__main__":
    # MinIO server configuration
    MINIO_URL = os.getenv("MINIO_URL", "http://localhost:9000")
    ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "ROOT_USER")
    SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "TOOR_PASSWORD")
    BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "papers")
    create_bucket(
        s3_url=MINIO_URL,
        s3_access_key=ACCESS_KEY,
        s3_secret_key=SECRET_KEY,
        bucket_name=BUCKET_NAME,
    )
