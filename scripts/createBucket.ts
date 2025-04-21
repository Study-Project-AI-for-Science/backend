// filepath: scripts/createBucket.ts
import { S3Client, ListBucketsCommand, CreateBucketCommand } from "@aws-sdk/client-s3"

// MinIO/S3 server configuration from environment variables
const MINIO_URL = process.env.MINIO_URL || "http://localhost:9000"
const ACCESS_KEY = process.env.MINIO_ROOT_USER || "ROOT_USER"
const SECRET_KEY = process.env.MINIO_ROOT_PASSWORD || "TOOR_PASSWORD"
const BUCKET_NAME = process.env.MINIO_BUCKET_NAME || "papers"
const REGION = process.env.MINIO_REGION || "us-east-1"

// Configure the AWS SDK v3 S3Client
const s3 = new S3Client({
    endpoint: MINIO_URL,
    region: REGION,
    credentials: {
        accessKeyId: ACCESS_KEY,
        secretAccessKey: SECRET_KEY,
    },
    forcePathStyle: true, // Required for MinIO
})

async function createBucketIfNotExists(bucketName: string) {
    try {
        // Check if the bucket already exists
        const listResult = await s3.send(new ListBucketsCommand({}))
        const bucketExists = (listResult.Buckets || []).some(
            (bucket) => bucket.Name === bucketName
        )

        if (bucketExists) {
            console.log(`Bucket '${bucketName}' already exists.`)
        } else {
            await s3.send(new CreateBucketCommand({ Bucket: bucketName }))
            console.log(`Bucket '${bucketName}' created successfully!`)
        }
    } catch (err: any) {
        if (err && typeof err === "object" && "message" in err) {
            console.error(`Error interacting with S3: ${err.message}`)
        } else {
            console.error("Error interacting with S3:", err)
        }
    }
}

// Run the function
createBucketIfNotExists(BUCKET_NAME)