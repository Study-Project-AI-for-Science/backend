// import { spawn } from "child_process"
// import path from "path"
// import { fileURLToPath } from "url"

// // Get the directory name in ES module scope
// const __filename = fileURLToPath(import.meta.url)
// const __dirname = path.dirname(__filename)

// // Determine the absolute path to the Python script
// // Assuming latexUtils.ts is in backend/packages/latexParser/
// // and main.py is in backend/modules/latex_parser/
// const pythonScriptPath = path.resolve(__dirname, "../../modules/latex_parser/main.py")
// const pythonExecutable = process.env.PYTHON_EXECUTABLE || "python3" // Or just 'python'

// /**
//  * Helper function to run the Python script and get JSON output.
//  * @param functionName The name of the Python function to call.
//  * @param args Arguments for the Python script.
//  * @returns Promise resolving with the parsed JSON output.
//  */
// async function runPythonScript<T>(functionName: string, args: Record<string, string>): Promise<T> {
//   const scriptArgs = ["--function", functionName]
//   for (const [key, value] of Object.entries(args)) {
//     scriptArgs.push(`--${key}`, String(value))
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
//         console.error(
//           `Python script (${pythonScriptPath}) stderr for ${functionName}: ${stderrData}`,
//         )
//         try {
//           const errorJson = JSON.parse(stderrData)
//           reject(
//             new Error(
//               `Python script error (${functionName}): ${errorJson.error || stderrData} (Type: ${errorJson.type || "Unknown"})`,
//             ),
//           )
//         } catch (e) {
//           reject(
//             new Error(
//               `Python script exited with code ${code} for function ${functionName}. Stderr: ${stderrData}`,
//             ),
//           )
//         }
//       } else {
//         try {
//           if (!stdoutData.trim()) {
//             resolve(null as T) // Handle cases where Python returns None or empty output
//           } else {
//             const result = JSON.parse(stdoutData)
//             resolve(result as T)
//           }
//         } catch (error) {
//           console.error(`Failed to parse Python script output for ${functionName}: ${stdoutData}`)
//           reject(new Error(`Failed to parse Python script output for ${functionName}: ${error}`))
//         }
//       }
//     })

//     pythonProcess.on("error", (error) => {
//       console.error(`Failed to start Python script (${pythonScriptPath}): ${error}`)
//       reject(new Error(`Failed to start Python script for ${functionName}: ${error.message}`))
//     })
//   })
// }

// export async function extractReferences(sourceDir: string): Promise<Record<string, any>[]> {
//   // Call the python script to extract references
//   const result = await runPythonScript<Record<string, any>[]>("extract_references", {
//     source_dir: sourceDir,
//   })
//   return result ?? [] // Return empty array if result is null/undefined
// }

// export async function parseLatexToMarkdown(sourceDirOrFilePath: string): Promise<string> {
//   // Call the python script to parse LaTeX to Markdown
//   // The python script expects the argument named 'path'
//   // It returns an object like { markdown: "..." }
//   const result = await runPythonScript<{ markdown: string }>("parse_latex_to_markdown", {
//     path: sourceDirOrFilePath,
//   })
//   return result?.markdown ?? "" // Return the markdown string or empty string if result is null/undefined
// }
