import { papers } from "~~/packages/database/schema"
import * as crypto from "node:crypto"
import { uuidv7 } from "uuidv7"

export default defineEventHandler(async (event) => {
  const formData = await readFormData(event)
  if (!formData) throw createError({ statusCode: 400, statusMessage: "No form data provided" })

  const file = formData.get("file") as File
  if (!file) throw createError({ statusCode: 400, statusMessage: "No file provided" })

  const paperId = uuidv7()

  // Upload file to s3 storage
  await useS3Storage().setItemRaw(paperId, file)

  const fileHash = await fileToSHA256Hash(file)
  const fileUrl = paperId

  // Write paper to database
  const [paper] = await useDrizzle()
    .insert(papers)
    .values({
      id: paperId,
      fileHash: fileHash,
      fileUrl: fileUrl,
      authors: "",
      title: "",
      abstract: "",
    })
    .returning()

  if (!paper) throw createError({ statusCode: 500, statusMessage: "Failed to insert paper" })

  // Background jobs
  // await arxivPaperMetadata()
  // -> await arxivPaperDownload()
  // -> await arxivPaperReferences()
  // -> await paperLaTeXToMarkdown()
  // -> await paperEmbeddings()

  return paper
})

// Helper
async function fileToSHA256Hash(file: File): Promise<string> {
  const arrayBuffer = await file.arrayBuffer()
  const buffer = Buffer.from(arrayBuffer)
  return crypto.createHash("sha256").update(buffer).digest("hex")
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
