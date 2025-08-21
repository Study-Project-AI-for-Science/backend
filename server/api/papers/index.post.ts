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
import { eq, sql } from "drizzle-orm"

import { spawn } from "child_process"
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
  event.waitUntil(
    arxivPaperMetadata({ paper }).catch((err) => {
      console.error("arxivPaperMetadata failed", err)
    })
  )
  // Handle the content processing using ollama_service
  event.waitUntil(
    pdfPaperHandling({ paper }).catch((err) => {
      console.error("ollamaService failed", err)
    })
  )

  return paper
})

 
// Zod schemas mirroring Pydantic models for document extraction results
export const DocumentMetadataSchema = z.object({
  title: z.string().default(""),
  authors: z.array(z.string()).default([]),
  journal: z.string().default(""),
  field_of_study: z.string().default(""),
  publication_date: z.string().default(""),
  doi: z.string().default(""),
  keywords: z.array(z.string()).default([]),
})

export type DocumentMetadata = z.infer<typeof DocumentMetadataSchema>

export const SemanticChunkSchema = z.object({
  id: z.string(),
  content: z.string(),
  content_vectors: z.array(z.number()).default([]).optional(),
  page: z.number().int(),
  section: z.string().default(""),
  type: z.enum([
    "paragraph",
    "figure",
    "equation",
    "heading",
    "table",
    "caption",
    "list",
    "proper_name",
    "reference",
  ]),
  caption: z.string().nullable().optional(),
  format: z.enum(["LaTeX", "text", "HTML", "png", "img"]).default("text"),
})

export type SemanticChunk = z.infer<typeof SemanticChunkSchema>

export const ReferenceSchema = z.object({
  title: z.string(),
  authors: z.array(z.string()).default([]),
  field_of_study: z.string().nullable().optional(),
  journal: z.string().nullable().optional(),
  publication_date: z.string().nullable().optional(),
  doi: z.string().nullable().optional(),
  keywords: z.array(z.string()).default([]),
})

export type Reference = z.infer<typeof ReferenceSchema>

export const DocumentExtractionResultSchema = z.object({
  document_metadata: DocumentMetadataSchema,
  semantic_chunks: z.array(SemanticChunkSchema),
  references: z.array(ReferenceSchema),
})

export type DocumentExtractionResult = z.infer<typeof DocumentExtractionResultSchema>


async function pdfPaperHandling({ paper }: { paper: typeof papers.$inferSelect }, withReferences: boolean = true): Promise<void> {
  const paper_source = await useS3Storage().getItemRaw(paper.id!)
  if (paper_source) {
    // call ollamaService /paper-content at OLLAMA_SERVICE:8000/paper-content
    // Ollama /paper-content expects multipart/form-data with a file field
    const form = new FormData()
    // paper_source can be a File/Blob or a Buffer/ArrayBuffer — provide a filename for the upload
    // If paper_source is a Node Buffer/ArrayBuffer convert to a Blob-like value if necessary
    form.append(
      "file",
      paper_source,
      (paper_source && (paper_source as any).name) || `${paper.id}.pdf`,
    )

    const contentResponse = await fetch(`${process.env.OLLAMA_SERVICE}/paper-content`, {
      method: "POST",
      // Do not set Content-Type header manually; fetch will add the proper multipart boundary
      body: form,
    })

    if (!contentResponse.ok) {
      const errText = await contentResponse.text().catch(() => "<no body>")
      throw new Error(`paper-content request failed: ${contentResponse.status} ${contentResponse.statusText} - ${errText}`)
    }

    const contentJson = await contentResponse.json().catch((err) => {
      throw new Error(`Failed to parse paper-content JSON: ${String(err)}`)
    })

    const parsed = DocumentExtractionResultSchema.safeParse(contentJson)
    if (!parsed.success) {
      console.error("Document extraction validation failed:", parsed.error.format ? parsed.error.format() : parsed.error)
      throw new Error("Invalid DocumentExtractionResult from paper-content")
    }

    const extractionResult: DocumentExtractionResult = parsed.data
    console.info(`Validated document extraction for paper ${paper.id}: ${extractionResult.semantic_chunks.length} chunks, ${extractionResult.references.length} references`)

    // call ollamaService /paper-embeddings
    const paperEmbeddingsResponse = await fetch(`${process.env.OLLAMA_SERVICE}/paper-embeddings`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ "semantic_chunks": extractionResult.semantic_chunks }),
    })
    if (!paperEmbeddingsResponse.ok) {
      const errText = await paperEmbeddingsResponse.text().catch(() => "<no body>")
      throw new Error(`paper-embeddings request failed: ${paperEmbeddingsResponse.status} ${paperEmbeddingsResponse.statusText} - ${errText}`)
    }

    const paperEmbeddingsJson = await paperEmbeddingsResponse.json().catch((err) => {
      throw new Error(`Failed to parse paper-embeddings JSON: ${String(err)}`)
    })

    const paperEmbeddingsParsed = z.array(SemanticChunkSchema).safeParse(paperEmbeddingsJson)
    if (!paperEmbeddingsParsed.success) {
      console.error(
      "Paper embeddings validation failed:",
      paperEmbeddingsParsed.error.format ? paperEmbeddingsParsed.error.format() : paperEmbeddingsParsed.error,
      )
      throw new Error("Invalid SemanticChunk[] from paper-embeddings")
    }

    const paperEmbeddingsResult: SemanticChunk[] = paperEmbeddingsParsed.data
    console.info(`Validated document embeddings for paper ${paper.id}: ${paperEmbeddingsResult.length} chunks`)


    // combine the document extraction result and embeddings. For each semantic chunk in the document extraction result, add a field content_vectors, where the corresponding embedding is stored. You can use the chunk's id to find the matching embedding. The combinedResults should be of type DocumentExtractionResult and should include everything of the extractionResult.
    const combinedResults: DocumentExtractionResult = {
      ...extractionResult,
      semantic_chunks: extractionResult.semantic_chunks.map((chunk) => {
        const matchingEmbedding = paperEmbeddingsResult.find((embedding) => embedding.id === chunk.id)
        return {
          ...chunk,
          content_vectors: matchingEmbedding ? matchingEmbedding.content_vectors : [],
        }
      }),
    }
    console.info(`Combined document extraction and embeddings for paper ${paper.id}`)

    await useDrizzle()
      .update(papers)
      .set({
      title: combinedResults.document_metadata.title,
      authors: combinedResults.document_metadata.authors.join(", "),
      documentExtractionResult: JSON.stringify(combinedResults),
      })
      .where(eq(papers.id, paper.id))

    // if dont already exists paper references for this paper.id, then create them
    if (withReferences) {

      const existingReferences = await useDrizzle()
        .select()
        .from(paperReferences)
        .where(eq(paperReferences.paperId, paper.id))

      if (existingReferences.length === 0) {
        // Map combinedResults.references (Reference[]) into ReferenceInput[] expected by paperReferencesInsertMany
        const referenceInputs: ReferenceInput[] = combinedResults.references.map((ref, idx) => {
          const byDoi = ref.doi?.replace(/[^A-Za-z0-9]+/g, "_")
          const byTitle = ref.title
            ? ref.title.toLowerCase().replace(/[^a-z0-9]+/g, "_").slice(0, 50)
            : undefined
          const citationKey = byDoi || byTitle || `ref_${idx}`

          return {
            id: citationKey,
            title: ref.title || "",
            authors: Array.isArray(ref.authors) ? ref.authors.join(", ") : "",
            raw_bibtex: JSON.stringify(ref),
            // Preserve additional fields for downstream use/search
            field_of_study: ref.field_of_study ?? null,
            journal: ref.journal ?? null,
            publication_date: ref.publication_date ?? null,
            doi: ref.doi ?? null,
            keywords: ref.keywords ?? [],
          } as ReferenceInput
        })

        // call the paperReferencesInsertMany function with proper signature
        await paperReferencesInsertMany(paper.id!, referenceInputs)
      }
    }

  }
}

async function arxivPaperMetadata({ paper }: { paper: typeof papers.$inferInsert }): Promise<void> {
  const sourceDir = await arxivPaperDownload({ paper }) // ✅
  if (sourceDir) {
    await arxivPaperReferences({ paper }, sourceDir)
    const markdownContent = await paperLaTeXToMarkdown({ paper }, sourceDir)
    // await paperEmbeddingsMarkdownCreate({ paper }, markdownContent)
    console.info(`Finished processing ${paper.id} arXiv paper metadata`)
  } else {
    console.error("No source directory found for the arXiv paper")
    //For now switch to processing all paper's context the same way
    // await paperEmbeddingsCreate({ paper }) // Fallback to embeddings using the PDF text
  }
  
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

  //TODO If the paper is not from arxiv we will switch to the PDF-pipeline
  if (!arxivIds) throw new Error("No arXiv IDs found in the PDF")

  for (const arxivId of arxivIds) {
    // download the arxiv paper
    const res = await fetch(`https://export.arxiv.org/api/query?id_list=${arxivId}`)
    const xml = await res.text()
    // parse xml to json
    const data = JSON.parse(parser.toJson(xml)) as unknown as z.infer<typeof arxivPaperSchema>

    console.log(data)

    //! This should be handled in a more general way, e.g. by checking the schema
    if (data.feed.entry.id === "http://arxiv.org/api/errors#incorrect_id_format_for_1707.08567a") {
      continue
    }

    // hurraayy we found a paper
    const authorArray = Array.isArray(data.feed.entry.author)
      ? data.feed.entry.author
      : [data.feed.entry.author]

    const foundPaper = {
      title: data.feed.entry.title,
      authors: authorArray.map((author) => author.name).join(", "),
      abstract: data.feed.entry.summary,
      onlineUrl: `http://arxiv.org/abs/${arxivId}`,
    }

    // Use the new helper function to download source
    const extractedSourceDir = await downloadArxivSource(arxivId)

    if (!extractedSourceDir) {
      console.error(`Failed to download source for arXiv ID ${arxivId}`)
      continue
    }

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

// For now implemented the python script to convert LaTeX to Markdown
// TODO implement this in JavaScript/TypeScript directly
async function paperLaTeXToMarkdown(
  { paper }: { paper: typeof papers.$inferInsert },
  sourceDir: string,
): Promise<string> {
  const result = await runPythonScript<{ markdown: string }>("parse_latex_to_markdown", {
    path: sourceDir,
  })

  // Update the paper in the database with the markdown content
  await useDrizzle()
    .update(papers)
    .set({
      content: result?.markdown ?? "",
    })
    .where(eq(papers.id, paper.id!))

  console.info(`Updated paper ${paper.id} with markdown content`)
  return result?.markdown ?? "" // Return the markdown string or empty string if result is null/undefined
}

// async function paperEmbeddingsCreate({ paper }: { paper: typeof papers.$inferInsert }) {
//   try {
//     console.info(`Starting PDF embedding creation for paper ${paper.id}`)

//     // Get the PDF content from S3
//     const paperFile = await useS3Storage().getItemRaw(paper.id!)
//     const pdfFile = await extractText(paperFile)
//     const pdfText = pdfFile.text.join("\n\n")

//     if (!pdfText.trim()) {
//       console.warn(`No text content found for paper ${paper.id}`)
//       return
//     }

//     const ollamaService = process.env.OLLAMA_SERVICE || "http://localhost:8000"

//     console.info(`Creating PDF embeddings using Ollama Service`)

//     // Delegate embedding creation to the Ollama service
//     const response = await fetch(`${ollamaService}/paper-embeddings`, {
//       method: "POST",
//       headers: {
//         "Content-Type": "application/json",
//       },
//       body: JSON.stringify({ text: pdfText, paperId: paper.id }),
//     })
//     if (!response.ok) {
//       const errorText = await response.text()
//       throw new Error(`Embedding service error: ${response.status} - ${errorText}`)
//     }
//     console.info(`Embedding service accepted PDF text for paper ${paper.id}`)
//   } catch (error) {
//     console.error(`Failed to create PDF embeddings for paper ${paper.id}:`, error)
//   }
// }

/**
 * Chunk text into smaller pieces based on approximate token count
 * Uses a simple heuristic: ~4 characters per token
 */
// function chunkTextByTokens(text: string, maxTokens: number): string[] {
//   const maxChars = maxTokens * 4 // Rough approximation: 4 chars per token
//   const chunks: string[] = []

//   // Split by paragraphs first to maintain semantic boundaries
//   const paragraphs = text.split(/\n\s*\n/)

//   let currentChunk = ""

//   for (const paragraph of paragraphs) {
//     // If adding this paragraph would exceed the limit, save current chunk and start new one
//     if (currentChunk.length + paragraph.length > maxChars && currentChunk.length > 0) {
//       chunks.push(currentChunk.trim())
//       currentChunk = paragraph
//     } else {
//       // Add paragraph to current chunk
//       if (currentChunk.length > 0) {
//         currentChunk += "\n\n" + paragraph
//       } else {
//         currentChunk = paragraph
//       }
//     }

//     // If a single paragraph is too long, split it by sentences
//     if (currentChunk.length > maxChars) {
//       const sentences = currentChunk.split(/[.!?]+/)
//       let sentenceChunk = ""

//       for (const sentence of sentences) {
//         if (sentenceChunk.length + sentence.length > maxChars && sentenceChunk.length > 0) {
//           chunks.push(sentenceChunk.trim())
//           sentenceChunk = sentence
//         } else {
//           if (sentenceChunk.length > 0) {
//             sentenceChunk += ". " + sentence
//           } else {
//             sentenceChunk = sentence
//           }
//         }
//       }

//       currentChunk = sentenceChunk
//     }
//   }

//   // Add the last chunk if it has content
//   if (currentChunk.trim().length > 0) {
//     chunks.push(currentChunk.trim())
//   }

//   // Filter out very small chunks (less than 50 characters)
//   return chunks.filter((chunk): chunk is string => chunk != null && chunk.length >= 50)
// }

// async function paperEmbeddingsMarkdownCreate(
//   { paper }: { paper: typeof papers.$inferInsert },
//   markdownContent: string,
// ) {
//   try {
//     console.info(`Starting markdown embedding creation for paper ${paper.id}`)

//     if (!markdownContent.trim()) {
//       console.warn(
//         `No markdown content found for paper ${paper.id}, falling back to PDF embeddings`,
//       )
//       await paperEmbeddingsCreate({ paper })
//       return
//     }

//     const ollamaHost = process.env.OLLAMA_HOST || "http://localhost:11434"
//     const modelName = process.env.OLLAMA_EMBEDDING_MODEL || "mxbai-embed-large"

//     console.info(`Creating markdown embeddings using chunking strategy with model: ${modelName}`)

//     // Chunk the markdown content into smaller pieces
//     const chunks = chunkTextByTokens(markdownContent, 512)
//     console.info(`Split markdown content into ${chunks.length} chunks`)

//     // Process each chunk and create embeddings
//     for (let i = 0; i < chunks.length; i++) {
//       const chunk = chunks[i]

//       if (!chunk) {
//         console.warn(`Skipping empty chunk ${i} for paper ${paper.id}`)
//         continue
//       }

//       try {
//         // Use direct Ollama API to generate embeddings for this chunk
//         const response = await fetch(`${ollamaHost}/api/embeddings`, {
//           method: "POST",
//           headers: {
//             "Content-Type": "application/json",
//           },
//           body: JSON.stringify({
//             model: modelName,
//             prompt: chunk,
//           }),
//         })

//         if (!response.ok) {
//           const errorText = await response.text()
//           throw new Error(`Ollama API error for chunk ${i}: ${response.status} - ${errorText}`)
//         }

//         const data = await response.json()
//         const embedding = data.embedding

//         if (!embedding || !Array.isArray(embedding)) {
//           throw new Error(`Invalid embedding response from Ollama API for chunk ${i}`)
//         }

//         console.info(
//           `Generated embedding for chunk ${i + 1}/${chunks.length} (${embedding.length} dimensions)`,
//         )

//         // Create a hash of the chunk content for deduplication
//         const contentHash = crypto.createHash("sha256").update(chunk).digest("hex")

//         // Insert embedding into database with chunk index in modelVersion
//         await useDrizzle()
//           .insert(paperEmbeddings)
//           .values({
//             paperId: paper.id!,
//             embedding: embedding,
//             modelName: modelName,
//             modelVersion: `markdown-chunk-${i}`,
//             embeddingHash: contentHash,
//           })
//           .onConflictDoNothing()

//         console.info(`Successfully stored embedding for chunk ${i + 1}/${chunks.length}`)
//       } catch (chunkError) {
//         console.error(`Failed to process chunk ${i} for paper ${paper.id}:`, chunkError)
//         // Continue with other chunks even if one fails
//       }
//     }

//     console.info(`Completed markdown embeddings for paper ${paper.id} (${chunks.length} chunks)`)
//   } catch (error) {
//     console.error(`Failed to create markdown embeddings for paper ${paper.id}:`, error)
//     // Fallback to PDF embeddings if markdown embedding fails
//     console.info(`Falling back to PDF embeddings for paper ${paper.id}`)
//     await paperEmbeddingsCreate({ paper })
//   }
// }

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

  // Use process.cwd() to get the project root directory
  const projectRoot = process.cwd()
  const pythonScriptPath = path.resolve(projectRoot, "modules/latex_parser/main.py")
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
    // Process reference to find/insert ArXiv papers
    const referencedPaperId = await processReferenceWithArxivId(ref)

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

/**
 * ARXIV REFERENCE PROCESSING FUNCTIONS
 *
 * These functions handle the recursive processing of arXiv papers found in references:
 * 1. findArxivIdInReference - Searches reference fields for arXiv IDs
 * 2. findPaperByArxivId - Checks if paper already exists in database
 * 3. insertPaperFromArxivId - Downloads and inserts new arXiv papers
 * 4. downloadArxivSource - Downloads LaTeX source from arXiv
 * 5. processReferenceWithArxivId - Main processing logic for references
 */

// Helper function to find the ArXiv ID in reference fields
function findArxivIdInReference(reference: ReferenceInput): string | null {
  const pattern = /\d{4}\.\d{5}/
  const fieldsToSearch = [
    reference.title,
    reference.authors,
    reference.raw_bibtex,
    ...Object.values(reference).filter((v) => typeof v === "string"),
  ]

  for (const field of fieldsToSearch) {
    if (!field) continue
    const match = field.match(pattern)
    if (match) return match[0]
  }
  return null
}

// Helper function to find existing paper by ArXiv ID
async function findPaperByArxivId(arxivId: string): Promise<typeof papers.$inferSelect | null> {
  const paper = await useDrizzle()
    .select()
    .from(papers)
    .where(sql`${papers.onlineUrl} LIKE ${"%" + arxivId + "%"}`)
    .limit(1)

  return paper[0] || null
}

// Main function to insert a paper from ArXiv ID
async function insertPaperFromArxivId(
  arxivId: string,
  shouldProcessReferences: boolean = true,
): Promise<string> {
  try {
    // Fetch metadata from arXiv API
    const res = await fetch(`https://export.arxiv.org/api/query?id_list=${arxivId}`)
    const xml = await res.text()
    const data = JSON.parse(parser.toJson(xml)) as unknown as z.infer<typeof arxivPaperSchema>

    // Check for API errors
    if (data.feed.entry.id === "http://arxiv.org/api/errors#incorrect_id_format_for_1707.08567a") {
      throw new Error(`Invalid arXiv ID format: ${arxivId}`)
    }

    // Extract paper metadata
    const authorArray = Array.isArray(data.feed.entry.author)
      ? data.feed.entry.author
      : [data.feed.entry.author]

    const foundPaper = {
      title: data.feed.entry.title,
      authors: authorArray.map((author) => author.name).join(", "),
      abstract: data.feed.entry.summary,
      onlineUrl: `http://arxiv.org/abs/${arxivId}`,
    }

    // Download the PDF from arXiv
    const pdfUrl = `https://arxiv.org/pdf/${arxivId}.pdf`
    const pdfResponse = await fetch(pdfUrl)
    if (!pdfResponse.ok) {
      throw new Error(`Failed to download PDF for arXiv ID ${arxivId}`)
    }

    const pdfBuffer = await pdfResponse.arrayBuffer()
    const pdfFile = new File([pdfBuffer], `${arxivId}.pdf`, { type: "application/pdf" })

    // Generate new paper ID and upload to S3
    const paperId = uuidv7()
    await useS3Storage().setItemRaw(paperId, pdfFile)

    const fileHash = await fileToSHA256Hash(pdfFile)
    const fileUrl = `${process.env.NUXT_S3_ENDPOINT}/${process.env.NUXT_S3_BUCKET}/${paperId}`

    
    // Insert paper into database
    const [paper] = await useDrizzle()
      .insert(papers)
      .values({
        id: paperId,
        title: foundPaper.title,
        authors: foundPaper.authors,
        abstract: foundPaper.abstract,
        fileHash: fileHash,
        fileUrl: fileUrl,
        onlineUrl: foundPaper.onlineUrl,
      })
      .returning()

    if (!paper) throw new Error(`Failed to insert paper for arXiv ID ${arxivId}`)

    await pdfPaperHandling({ paper }, false)

    console.info(`Successfully inserted paper ${paper.id} for arXiv ID ${arxivId}`)

    // Download source and try markdown embeddings first, regardless of reference processing
    try {
      const sourceDir = await downloadArxivSource(arxivId)
      if (sourceDir) {
        // Only process references for the main paper to avoid infinite recursion
        if (shouldProcessReferences) {
          await arxivPaperReferences({ paper }, sourceDir)
        }
        // Always try markdown embeddings first since we have LaTeX source
  const markdownContent = await paperLaTeXToMarkdown({ paper }, sourceDir)
  // Optionally, create embeddings from markdown here. For now, rely on downstream processing.
      } else {
        // Fallback to PDF embeddings if source download failed
  await pdfPaperHandling({ paper })
      }
    } catch (error) {
      console.error(`Error processing arXiv ${arxivId}:`, error)
      // Continue without failing - create embeddings from PDF
  await pdfPaperHandling({ paper })
    }

    return paperId
  } catch (error) {
    console.error(`Failed to insert paper from arXiv ID ${arxivId}:`, error)
    throw error
  }
}

// Helper function to download arXiv source
async function downloadArxivSource(arxivId: string): Promise<string> {
  try {
    const sourceUrl = `https://arxiv.org/src/${arxivId}`
    const sourceRes = await fetch(sourceUrl)
    if (!sourceRes.ok) {
      console.error(`Failed to download source from ${sourceUrl}: ${sourceRes.statusText}`)
      return ""
    }

    const sourceBuffer = await sourceRes.arrayBuffer()
    const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), `arxiv-${arxivId}-`))
    const tarGzPath = path.join(tempDir, `${arxivId}.tar.gz`)

    await fs.writeFile(tarGzPath, Buffer.from(sourceBuffer))

    await tar.extract({
      file: tarGzPath,
      cwd: tempDir,
    })

    await fs.unlink(tarGzPath)

    return tempDir
  } catch (error) {
    console.error(`Error downloading arXiv source for ${arxivId}:`, error)
    return ""
  }
}

// Process reference to find and insert ArXiv papers
async function processReferenceWithArxivId(reference: ReferenceInput): Promise<string | null> {
  try {
    // Search for ArXiv ID in reference fields
    const arxivId = findArxivIdInReference(reference)
    if (!arxivId) return null

    console.info(`Found arXiv ID ${arxivId} in reference: ${reference.id}`)

    // Check if paper already exists in database
    const existingPaper = await findPaperByArxivId(arxivId)
    if (existingPaper) {
      console.info(`Paper for arXiv ID ${arxivId} already exists: ${existingPaper.id}`)
      return existingPaper.id
    }

    // Insert new paper WITHOUT processing its references to avoid recursion
    console.info(`Inserting new paper for arXiv ID ${arxivId}`)
    const newPaperId = await insertPaperFromArxivId(arxivId, false)
    return newPaperId
  } catch (error) {
    console.error(`Error processing reference with arXiv ID:`, error)
    return null
  }
}
