import { papers, paperEmbeddings, paperReferences } from "~~/packages/database/schema"
import { extractText, getDocumentProxy } from "unpdf"
import parser from "xml2json"

import * as crypto from "node:crypto"
import * as fs from "node:fs/promises"
import * as path from "node:path"
import * as os from "node:os"
import * as tar from "tar"
import { uuidv7 } from "uuidv7"
import { z } from "zod"
import { eq } from "drizzle-orm"

import { spawn } from "child_process"
import { fileURLToPath } from "url"
import { Console } from "node:console"

export default defineEventHandler(async (event) => {
  const formData = await readFormData(event)
  if (!formData) throw createError({ statusCode: 400, statusMessage: "No form data provided" })

  const file = formData.get("file") as File
  if (!file) throw createError({ statusCode: 400, statusMessage: "No file provided" })

  const paperId = uuidv7()

  // Upload file to s3 storage
  await useS3Storage().setItemRaw(paperId, file)

  const fileHash = await fileToSHA256Hash(file)
  const fileUrl = `${process.env.NUXT_S3_ENDPOINT}/${process.env.NUXT_S3_BUCKET}/${paperId}`

  // Write paper to database
  const [paper] = await useDrizzle()
    .insert(papers)
    .values({
      id: paperId,
      title: "",
      authors: "",
      abstract: "",
      fileHash: fileHash,
      fileUrl: fileUrl,
    })
    .returning()

  if (!paper) throw createError({ statusCode: 500, statusMessage: "Failed to insert paper" })
  else console.info(`Paper ${paper.id} inserted successfully`)

  // Extract metadata from arXiv paper in the background
  event.waitUntil(arxivPaperMetadata({ paper }))

  return paper
})

async function arxivPaperMetadata({ paper }: { paper: typeof papers.$inferInsert }): Promise<void> {
  // TODO:
  const sourceDir = await arxivPaperDownload({ paper }) // ✅
  if (sourceDir) {
    await arxivPaperReferences({ paper }, sourceDir)
    const markdownContent = await paperLaTeXToMarkdown({ paper }, sourceDir)
    await paperEmbeddingsMarkdownCreate({ paper }, markdownContent)
  } else {
    console.error("No source directory found for the arXiv paper")
    await paperEmbeddingsCreate({ paper }) // Fallback to embeddings using the PDF text
  }
  console.info(`Finished processing ${paper.id} arXiv paper metadata`)
}

async function arxivPaperDownload({
  paper,
}: {
  paper: typeof papers.$inferInsert
}): Promise<string> {
  // download the pdf
  const paperFile = await useS3Storage().getItemRaw(paper.id!)
  const pdfFile = await extractText(paperFile)
  const pdfText = pdfFile.text

  const pattern = /\d{4}\.\d{5}/
  // search with regex for all the arxiv ids
  const arxivIds = pdfText.join("\n\n").match(pattern)

  if (!arxivIds) throw new Error("No arXiv IDs found in the PDF")

  for (const arxivId of arxivIds) {
    // download the arxiv paper
    const res = await fetch(`https://export.arxiv.org/api/query?id_list=${arxivId}`)
    const xml = await res.text()
    // parse xml to json
    const data = JSON.parse(parser.toJson(xml)) as unknown as z.infer<typeof arxivPaperSchema>

    console.log(data)

    if (data.feed.entry.id === "http://arxiv.org/api/errors#incorrect_id_format_for_1707.08567a") {
      continue
    }

    // hurraayy we found a paper
    const foundPaper = {
      title: data.feed.entry.title,
      authors: data.feed.entry.author.map((author) => author.name).join(", "),
      abstract: data.feed.entry.summary,
      onlineUrl: `http://arxiv.org/abs/${arxivId}`,
    }

    // download the source from arxiv
    const sourceUrl = foundPaper.onlineUrl.replace("abs", "src")
    const sourceRes = await fetch(sourceUrl)
    if (!sourceRes.ok) {
      console.error(`Failed to download source from ${sourceUrl}: ${sourceRes.statusText}`)
      continue
    }
    // The source is a tar.gz file, we need to extract it to a temporary directory
    const sourceBuffer = await sourceRes.arrayBuffer()
    const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), `arxiv-${arxivId}-`))
    const tarGzPath = path.join(tempDir, `${arxivId}.tar.gz`)

    // Write the tar.gz file to temp directory
    await fs.writeFile(tarGzPath, Buffer.from(sourceBuffer))

    // Extract the tar.gz file
    await tar.extract({
      file: tarGzPath,
      cwd: tempDir,
    })

    // Remove the tar.gz file after extraction
    await fs.unlink(tarGzPath)

    const extractedSourceDir = tempDir

    // TODO: validate the found paper data using e.g. zod

    // update the database
    await useDrizzle()
      .update(papers)
      .set({
        title: foundPaper.title,
        authors: foundPaper.authors,
        abstract: foundPaper.abstract,
        onlineUrl: foundPaper.onlineUrl,
      })
      .where(eq(papers.id, paper.id!))

    return extractedSourceDir
  }
  return ""
}

export const arxivPaperSchema = z.object({
  feed: z.object({
    link: z.object({ _href: z.string(), _rel: z.string(), _type: z.string() }),
    title: z.object({ _type: z.string(), __text: z.string() }),
    id: z.string(),
    updated: z.string(),
    totalResults: z.object({
      "_xmlns:opensearch": z.string(),
      __prefix: z.string(),
      __text: z.string(),
    }),
    startIndex: z.object({
      "_xmlns:opensearch": z.string(),
      __prefix: z.string(),
      __text: z.string(),
    }),
    itemsPerPage: z.object({
      "_xmlns:opensearch": z.string(),
      __prefix: z.string(),
      __text: z.string(),
    }),
    entry: z.object({
      id: z.string(),
      updated: z.string(),
      published: z.string(),
      title: z.string(),
      summary: z.string(),
      author: z.array(z.object({ name: z.string() })),
      comment: z.object({
        "_xmlns:arxiv": z.string(),
        __prefix: z.string(),
        __text: z.string(),
      }),
      link: z.array(
        z.union([
          z.object({ _href: z.string(), _rel: z.string(), _type: z.string() }),
          z.object({
            _title: z.string(),
            _href: z.string(),
            _rel: z.string(),
            _type: z.string(),
          }),
        ]),
      ),
      primary_category: z.object({
        "_xmlns:arxiv": z.string(),
        _term: z.string(),
        _scheme: z.string(),
        __prefix: z.string(),
      }),
      category: z.array(z.object({ _term: z.string(), _scheme: z.string() })),
    }),
    _xmlns: z.string(),
  }),
})

async function arxivPaperReferences(
  { paper }: { paper: typeof papers.$inferInsert },
  sourceDir: string,
) {
  const references = await runPythonScript<Record<string, any>[]>("extract_references", {
    source_dir: sourceDir,
  })

  if (references.length > 0) {
    console.info("Inserting references into the database")
    try {
      // Map references to ReferenceInput type
      const referenceInputs = references.map((ref) => ({
        id: ref.id ?? "",
        title: ref.title ?? "",
        authors: ref.authors ?? "",
        raw_bibtex: ref.raw_bibtex ?? "",
        ...ref,
      }))
      await paperReferencesInsertMany(paper.id!, referenceInputs)
    } catch (error) {
      console.error("Error inserting references into the database:", error)
    }
  }
}

async function paperLaTeXToMarkdown(
  { paper }: { paper: typeof papers.$inferInsert },
  sourceDir: string,
): Promise<string> {
  // TODO
  return ""
}

async function paperEmbeddingsCreate({ paper }: { paper: typeof papers.$inferInsert }) {
  // TODO
}

async function paperEmbeddingsMarkdownCreate(
  { paper }: { paper: typeof papers.$inferInsert },
  markdownContent: string,
) {
  // TODO
}

// Helper
async function fileToSHA256Hash(file: File): Promise<string> {
  const arrayBuffer = await file.arrayBuffer()
  const buffer = Buffer.from(arrayBuffer)
  return crypto.createHash("sha256").update(buffer).digest("hex")
}

/**
 * Helper function to run the Python script and get JSON output.
 * @param functionName The name of the Python function to call.
 * @param args Arguments for the Python script.
 * @returns Promise resolving with the parsed JSON output.
 */
async function runPythonScript<T>(functionName: string, args: Record<string, string>): Promise<T> {
  const scriptArgs = ["--function", functionName]
  for (const [key, value] of Object.entries(args)) {
    scriptArgs.push(`--${key}`, String(value))
  }

  const __filename = fileURLToPath(import.meta.url)
  const __dirname = path.dirname(__filename)

  const pythonScriptPath = path.resolve(__dirname, "../../modules/latex_parser/main.py")
  const pythonExecutable = process.env.PYTHON_EXECUTABLE || "python3"

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
            resolve(null as T) // Handle cases where Python returns None or empty output
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

export interface ReferenceInput {
  id: string // Citation key
  title: string
  authors: string
  raw_bibtex: string
  [key: string]: any // Allow additional fields like booktitle, year, etc.
}

export async function paperReferencesInsertMany(
  paperId: string,
  references: ReferenceInput[],
): Promise<number> {
  if (!references || references.length === 0) {
    console.warn("No references provided to insert.")
    // throw new Error("References list cannot be empty."); // Or a custom ValueError
    return 0
  }

  // Process each reference to find/insert ArXiv papers and get their IDs
  const valuesToInsertPromises = references.map(async (ref) => {
    //! TODO: Needs to be reimplemented
    //const referencedPaperId = await processReferenceWithArxivId(ref, "/tmp/ref_papers")
    // Set referencePaperId to null instead of a non-existent ID
    const referencedPaperId = null

    // Separate known fields from the rest to store in 'fields'
    const { id, type, title, authors, raw_bibtex, ...otherFields } = ref

    return {
      paperId: paperId, // The ID of the paper containing this reference list
      referenceKey: id, // The citation key (e.g., "turbo")
      referencePaperId: referencedPaperId, // ID of the referenced paper if found on ArXiv, otherwise null
      rawBibtex: raw_bibtex,
      title: title,
      authors: authors, // Map input 'authors' to schema 'authors'
      fields: otherFields, // Store remaining fields as JSON
      // Potentially map other specific fields if needed, e.g., type: type
    }
  })

  // Wait for all reference processing to complete
  const valuesToInsert = await Promise.all(valuesToInsertPromises)

  try {
    // Assuming paperReferences is the Drizzle schema object for the join table
    const result = await useDrizzle()
      .insert(paperReferences)
      .values(valuesToInsert)
      .returning({ insertedId: paperReferences.id }) // Return inserted IDs or count

    console.log(`Successfully inserted ${result.length} references for paper ${paperId}.`)
    return result.length
  } catch (error) {
    console.error(`Database error inserting references for paper ${paperId}:`, error)
    // Consider throwing a custom DatabaseError
    throw error // Re-throw the caught error
  }
}

//   // Temporary folder
//   const tempDir = os.tmpdir()
//   const filePath = join(tempDir, fileName)
//   await fs.writeFile(filePath, fileBuffer)

//   console.log(`Saved uploaded file temporarily to ${filePath}`)
//   console.log(`Title: ${title || "Not provided"}, Authors: ${authors || "Not provided"}`)

//   let arxivPaperId = ""
//   let abstract = ""
//   let paperUrl = ""
//   let published = ""
//   let updated = ""
//   let markdownContent = ""
//   let references: Record<string, any>[] = []
//   let processReferences = true

//   const arxivPaperMetadata = await getArxivMetadata(filePath)
//   if (arxivPaperMetadata?.arxiv_id) {
//     arxivPaperId = arxivPaperMetadata.arxiv_id || ""
//     title = arxivPaperMetadata.title || title
//     authors = arxivPaperMetadata.authors || authors
//     abstract = arxivPaperMetadata.abstract || ""
//     paperUrl = arxivPaperMetadata.url || ""
//     published = arxivPaperMetadata.published_date || ""
//     updated = arxivPaperMetadata.updated_date || ""

//     // create a temporary directory for the paper source
//     const tempDir = os.tmpdir()

//     const paperPath = await paperDownloadArxivId(arxivPaperId, tempDir)
//     let sourceDir = paperPath.endsWith(".pdf") ? paperPath.slice(0, -4) : paperPath
//     // let sourceDir = join(tempDir, arxivPaperId.replace(".", ""))

//     // if source dir doesn't exist, use temp_dir as source dir and log error
//     try {
//       await fs.access(sourceDir)
//     } catch (error) {
//       console.error(`Source directory ${sourceDir} does not exist. Using temp_dir as source dir.`)
//       sourceDir = tempDir
//     }

//     try {
//       markdownContent = await parseLatexToMarkdown(sourceDir)
//       console.info(`Parsed LaTeX to Markdown successfully`)
//     } catch (error) {
//       console.error(`Failed to parse LaTeX to Markdown: ${error}`)
//       markdownContent = ""
//     }

//     console.info("Extracting references from source directory")
//     references = await extractReferences(sourceDir)
//     console.info(`Extracted ${references.length} references`)
//   } else {
//     console.info("No arXiv ID found in the uploaded paper")
//     const paperInfo = await getPaperInfo(filePath)
//     if (paperInfo) {
//       title = paperInfo.title || title
//       authors = paperInfo.authors || authors
//       abstract = paperInfo.abstract || ""
//     }

//     // TODO Not markdown atm I guess?
//     markdownContent = await extractTextFromPdf(filePath)
//     console.info(`Extracted text from PDF successfully`)
//   }

//   //! TODO Not working atm
//   if (references.length <= 0) {
//     console.info("Skipping reference processing")
//     processReferences = false
//     // references = await extractReferencesFromFile(filePath)
//     // console.info(`Extracted ${references.length} references from file`)
//   }
//   // Insert the paper into the database
//   // The paperInsert function handles cases where title or authors are empty
//   // TODO: Handle case where paper is found, but no references are found
//   const paperId = await paperInsert(
//     filePath,
//     title,
//     authors,
//     abstract,
//     paperUrl,
//     published,
//     updated,
//     markdownContent,
//   )

//   if (references.length > 0) {
//     console.info("Inserting references into the database")
//     try {
//       // Map references to ReferenceInput type
//       const referenceInputs = references.map((ref) => ({
//         id: ref.id ?? "",
//         title: ref.title ?? "",
//         authors: ref.authors ?? "",
//         raw_bibtex: ref.raw_bibtex ?? "",
//         ...ref,
//       }))
//       await paperReferencesInsertMany(paperId, referenceInputs)
//     } catch (error) {
//       console.error("Error inserting references into the database:", error)
//       throw createError({
//         statusCode: 500,
//         statusMessage: "Failed to insert references into the database",
//       })
//     }
//   }

//   // Clean up the temporary file
//   try {
//     await fs.unlink(filePath)
//     console.log(`Temporary file ${filePath} has been deleted`)
//     // Also clean up the folder with the same path as filePath but without the .pdf extension
//     const folderPath = filePath.endsWith(".pdf") ? filePath.slice(0, -4) : filePath
//     try {
//       await fs.rm(folderPath, { recursive: true, force: true })
//       console.log(`Temporary folder ${folderPath} has been deleted`)
//     } catch (folderError) {
//       // It's ok if the folder doesn't exist
//       if (
//         typeof folderError === "object" &&
//         folderError !== null &&
//         "code" in folderError &&
//         (folderError as any).code !== "ENOENT"
//       ) {
//         console.error(`Failed to delete temporary folder ${folderPath}:`, folderError)
//       }
//     }
//   } catch (unlinkError) {
//     console.error(`Failed to delete temporary file ${filePath}:`, unlinkError)
//   }

//   return {
//     success: true,
//     paperId,
//     message: "Paper uploaded successfully",
//   }
// } catch (error: any) {
//   console.error("Error handling paper upload:", error)

//   // Handle specific error types if needed
//   if (error.statusCode) {
//     throw error // Pass through H3 errors with status codes
//   }

//   throw createError({
//     statusCode: 500,
//     statusMessage: `Failed to upload paper: ${error.message || "Unknown error"}`,
//   })
// }
