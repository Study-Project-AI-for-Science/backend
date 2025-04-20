import * as fs from "fs"
import * as path from "path"
import { Readable } from "stream"
import { URL } from "url"
import {
  S3Client,
  PutObjectCommand,
  GetObjectCommand,
  DeleteObjectCommand,
} from "@aws-sdk/client-s3"
import type { S3ClientConfig } from "@aws-sdk/client-s3"

import { uuidv7 } from "uuidv7"

// Configuration from environment variables with defaults
const endpoint = process.env.MINIO_URL || "http://localhost:9000"
const accessKeyId = process.env.MINIO_ROOT_USER || "ROOT_USER"
const secretAccessKey = process.env.MINIO_ROOT_PASSWORD || "TOOR_PASSWORD"
const bucketName = process.env.MINIO_BUCKET_NAME || "papers"
const region = process.env.MINIO_REGION || "us-east-1" // Default region, adjust if needed

const s3Config: S3ClientConfig = {
  endpoint: endpoint,
  region: region,
  credentials: {
    accessKeyId: accessKeyId,
    secretAccessKey: secretAccessKey,
  },
  forcePathStyle: true, // Required for MinIO
}

const s3Client = new S3Client(s3Config)

/**
 * Uploads a file to the S3 bucket.
 * @param filePath The local path to the file to upload.
 * @param objectKey Optional S3 object key. If not provided, uses the base name of the filePath.
 * @returns The URL of the uploaded file.
 */
export async function uploadFile(filePath: string): Promise<string> {
  const fileStream = fs.createReadStream(filePath)
  const fileId = uuidv7() // Generate a UUID v7 for the file ID
  const fileName = path.basename(filePath) // Extract the original filename
  const key = `${fileId}/${fileName}` // Construct the object key as fileId/fileName

  const uploadParams = {
    Bucket: bucketName,
    Key: key, // Use the new composite key
    Body: fileStream,
  }

  try {
    await s3Client.send(new PutObjectCommand(uploadParams))
    // Construct the URL manually. Ensure MinIO is configured for public access if needed.
    const baseUrl = endpoint.endsWith("/") ? endpoint.slice(0, -1) : endpoint
    const fileUrl = `${baseUrl}/${bucketName}/${key}` // Use the new key in the URL
    console.log(`File uploaded successfully. ${fileUrl}`)
    return fileUrl
  } catch (err) {
    console.error("Error uploading file:", err)
    throw err
  }
}

/**
 * Extracts the bucket name and object key from an S3 URL.
 * Assumes URL format like http(s)://endpoint/bucket/key
 * @param fileUrl The URL of the file in S3.
 * @returns An object containing the bucket name and object key.
 */
function parseS3Url(fileUrl: string): { bucket: string; key: string } {
  try {
    const parsedUrl = new URL(fileUrl)
    // Assumes path format /bucketName/objectKey...
    const pathParts = parsedUrl.pathname.split("/").filter((part) => part.length > 0)
    if (pathParts.length < 2) {
      throw new Error("Invalid S3 URL path format. Expected /bucket/key...")
    }
    const bucket = pathParts[0]!
    const key = pathParts.slice(1).join("/")
    return { bucket, key }
  } catch (error) {
    console.error("Error parsing S3 URL:", fileUrl, error)
    throw new Error(`Invalid S3 URL format: ${fileUrl}`)
  }
}

/**
 * Downloads a file from S3.
 * @param fileUrl The URL of the file in S3.
 * @param destinationPath The local path to save the downloaded file.
 */
export async function downloadFile(fileUrl: string, destinationPath: string): Promise<void> {
  const { bucket, key } = parseS3Url(fileUrl)

  // Ensure the destination directory exists
  const destinationDir = path.dirname(destinationPath)
  if (!fs.existsSync(destinationDir)) {
    fs.mkdirSync(destinationDir, { recursive: true })
  }

  const downloadParams = {
    Bucket: bucket, // Use bucket from parsed URL
    Key: key,
  }

  try {
    const { Body } = await s3Client.send(new GetObjectCommand(downloadParams))
    if (!Body || !(Body instanceof Readable)) {
      throw new Error("Could not retrieve file body from S3.")
    }
    const fileStream = fs.createWriteStream(destinationPath)
    await new Promise((resolve, reject) => {
      Body.pipe(fileStream)
        .on("error", (err) => reject(err))
        .on("close", () => resolve(null))
    })
    console.log(`File downloaded successfully to ${destinationPath}`)
  } catch (err) {
    console.error("Error downloading file:", err)
    throw err
  }
}

/**
 * Deletes a file from S3.
 * @param fileUrl The URL of the file in S3.
 */
export async function deleteFile(fileUrl: string): Promise<void> {
  const { bucket, key } = parseS3Url(fileUrl)

  const deleteParams = {
    Bucket: bucket, // Use bucket from parsed URL
    Key: key,
  }

  try {
    await s3Client.send(new DeleteObjectCommand(deleteParams))
    console.log(`File deleted successfully: ${fileUrl}`)
  } catch (err) {
    console.error("Error deleting file:", err)
    throw err
  }
}
