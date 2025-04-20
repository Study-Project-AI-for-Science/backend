import { spawn } from "child_process"
import path from "path"
import { fileURLToPath } from 'url'; // Import fileURLToPath

// Get the directory name in ES module scope
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Determine the absolute path to the Python script
// Assuming arxivUtils.ts is in backend/packages/retriever/
// and main.py is in backend/modules/retriever/arxiv/
const pythonScriptPath = path.resolve(__dirname, "../../modules/retriever/arxiv/main.py")
const pythonExecutable = process.env.PYTHON_EXECUTABLE || "python3" // Or just 'python'

/**
 * Helper function to run the Python script and get JSON output.
 * @param functionName The name of the Python function to call.
 * @param args Arguments for the Python script.
 * @returns Promise resolving with the parsed JSON output.
 */
async function runPythonScript<T>(functionName: string, args: Record<string, string>): Promise<T> {
  const scriptArgs = ["--function", functionName]
  for (const [key, value] of Object.entries(args)) {
    // Ensure value is a string before pushing
    scriptArgs.push(`--${key}`, String(value))
  }

  return new Promise((resolve, reject) => {
    const pythonProcess = spawn(pythonExecutable, [pythonScriptPath, ...scriptArgs])

    let stdoutData = ""
    let stderrData = ""

    pythonProcess.stdout.on("data", (data) => {
      stdoutData += data.toString()
    })

    pythonProcess.stderr.on("data", (data) => {
      stderrData += data.toString()
    })

    pythonProcess.on("close", (code) => {
      if (code !== 0) {
        console.error(
          `Python script (${pythonScriptPath}) stderr for ${functionName}: ${stderrData}`,
        )
        try {
          const errorJson = JSON.parse(stderrData)
          reject(
            new Error(
              `Python script error (${functionName}): ${errorJson.error || stderrData} (Type: ${errorJson.type || "Unknown"})`,
            ),
          )
        } catch (e) {
          reject(
            new Error(
              `Python script exited with code ${code} for function ${functionName}. Stderr: ${stderrData}`,
            ),
          )
        }
      } else {
        try {
          if (!stdoutData.trim()) {
            resolve(null as T) // Handle cases where Python returns None
          } else {
            const result = JSON.parse(stdoutData)
            resolve(result as T)
          }
        } catch (error) {
          console.error(`Failed to parse Python script output for ${functionName}: ${stdoutData}`)
          reject(new Error(`Failed to parse Python script output for ${functionName}: ${error}`))
        }
      }
    })

    pythonProcess.on("error", (error) => {
      console.error(`Failed to start Python script (${pythonScriptPath}): ${error}`)
      reject(new Error(`Failed to start Python script for ${functionName}: ${error.message}`))
    })
  })
}

export async function extractArxivIds(text: string): Promise<string[]> {
  // Call the python script to extract arXiv IDs
  const result = await runPythonScript<string[]>("extract_arxiv_ids", { text })
  return result ?? [] // Return empty array if result is null/undefined
}

export async function paperDownloadArxivId(arxivId: string, tempDir: string): Promise<string> {
  // Call the python script to download the paper by arXiv ID
  const result = await runPythonScript<string>("paper_download_arxiv_id", {
    arxiv_id: arxivId,
    output_dir: tempDir,
  })
  return result ?? "" // Return empty string if result is null/undefined (e.g., download failed)
}

// Add function to get metadata
export interface ArxivMetadata {
  title: string
  authors: string // Comma-separated string
  abstract: string
  url: string
  arxiv_id: string
  published_date: any // Consider using Date or string depending on format
  updated_date: any // Consider using Date or string depending on format
}

export async function getArxivMetadata(filePath: string): Promise<ArxivMetadata | null> {
  // Call the python script to get paper metadata from a file path
  // The python script returns an empty dict {} if metadata is not found, or null on error.
  const result = await runPythonScript<ArxivMetadata | {}>("paper_get_metadata", {
    file_path: filePath,
  })

  // Check if the result is an empty object, which indicates metadata not found by the script
  if (result && typeof result === "object" && Object.keys(result).length === 0) {
    return null
  }

  return result as ArxivMetadata | null
}
