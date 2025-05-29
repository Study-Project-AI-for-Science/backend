// import { spawn } from "child_process"
// import path from "path"
// import type { ReferenceInput } from "../database/db"
// import { fileURLToPath } from "url"

// // Get the directory name in ES module scope
// const __filename = fileURLToPath(import.meta.url)
// const __dirname = path.dirname(__filename)

// // Determine the absolute path to the Python script
// // Assuming ollamaUtils.ts is in backend/packages/ollama/
// // and main.py is in backend/modules/ollama/
// const pythonScriptPath = path.resolve(__dirname, "../../modules/ollama/main.py")
// const pythonExecutable = process.env.PYTHON_EXECUTABLE || "python3" // Or just 'python' if that's your command

// /**
//  * Helper function to run the Python script and get JSON output.
//  * @param functionName The name of the Python function to call.
//  * @param args Arguments for the Python script.
//  * @returns Promise resolving with the parsed JSON output.
//  */
// async function runPythonScript<T>(functionName: string, args: Record<string, string>): Promise<T> {
//   const scriptArgs = ["--function", functionName]
//   for (const [key, value] of Object.entries(args)) {
//     scriptArgs.push(`--${key}`, value)
//   }

//   return new Promise((resolve, reject) => {
//     const pythonProcess = spawn(pythonExecutable, [pythonScriptPath, ...scriptArgs])

//     let stdoutData = ""
//     let stderrData = ""

//     pythonProcess.stdout.on("data", (data) => {
//       stdoutData += data.toString()
//     })

//     pythonProcess.stderr.on("data", (data) => {
//       stderrData += data.toString()
//     })

//     pythonProcess.on("close", (code) => {
//       if (code !== 0) {
//         console.error(`Python script stderr: ${stderrData}`)
//         try {
//           // Try parsing stderr as JSON for structured errors
//           const errorJson = JSON.parse(stderrData)
//           reject(
//             new Error(`Python script error (${functionName}): ${errorJson.error || stderrData}`),
//           )
//         } catch (e) {
//           // If stderr wasn't JSON, use the raw string
//           reject(
//             new Error(
//               `Python script exited with code ${code} for function ${functionName}. Stderr: ${stderrData}`,
//             ),
//           )
//         }
//       } else {
//         try {
//           // Handle potential empty stdout for functions returning None/null
//           if (!stdoutData.trim()) {
//             resolve(null as T) // Or handle as appropriate for your types
//           } else {
//             const result = JSON.parse(stdoutData)
//             resolve(result as T)
//           }
//         } catch (error) {
//           console.error(`Failed to parse Python script output: ${stdoutData}`)
//           reject(new Error(`Failed to parse Python script output for ${functionName}: ${error}`))
//         }
//       }
//     })

//     pythonProcess.on("error", (error) => {
//       console.error(`Failed to start Python script: ${error}`)
//       reject(new Error(`Failed to start Python script for ${functionName}: ${error.message}`))
//     })
//   })
// }

// export async function generateEmbedding(text: string): Promise<number[]> {
//   // Call the python script to generate embeddings for a query string
//   // The python script for get_query_embeddings returns the embedding list directly.
//   const result = await runPythonScript<number[]>("get_query_embeddings", { query_string: text })
//   return result ?? [] // Return empty array if result is null/undefined
// }

// export async function getPaperInfo(
//   filePath: string,
// ): Promise<{ title: string; authors: string; abstract: string }> {
//   // Call the python script to get paper info
//   return runPythonScript<{ title: string; authors: string; abstract: string }>("get_paper_info", {
//     file_path: filePath,
//   })
// }

// export async function getPaperEmbeddings(
//   filePath: string,
// ): Promise<{ embeddings: number[][]; model_name?: string; model_version?: string }> {
//   // Call the python script to get paper embeddings
//   return runPythonScript<{ embeddings: number[][]; model_name?: string; model_version?: string }>(
//     "get_paper_embeddings",
//     { file_path: filePath },
//   )
// }

// export async function extractTextFromPdf(filePath: string): Promise<string> {
//   // Call the python script to extract text from PDF
//   // The python script prints the extracted text directly to stdout
//   const result = await runPythonScript<string>("extract_text", { file_path: filePath })
//   return result ?? "" // Return empty string if result is null/undefined
// }

// export async function extractReferencesFromFile(filePath: string): Promise<ReferenceInput[]> {
//   // TODO - Implement the logic to extract references from the file
//   // This is a placeholder implementation.
//   return []
// }
