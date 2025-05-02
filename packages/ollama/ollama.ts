import { createOllama } from "ollama-ai-provider"
import * as pdfjsLib from "pdfjs-dist"
import * as fs from "fs/promises"
import { z } from "zod"

// Define the environment variables with defaults
const OLLAMA_HOST = process.env.OLLAMA_HOST || "http://localhost:11434"
const OLLAMA_MODEL = process.env.OLLAMA_MODEL || "llama3.1"
const OLLAMA_EMBEDDING_MODEL = process.env.OLLAMA_EMBEDDING_MODEL || "mxbai-embed-large"
const OLLAMA_USERNAME = process.env.OLLAMA_USERNAME || ""
const OLLAMA_PASSWORD = process.env.OLLAMA_PASSWORD || ""
const OLLAMA_API_TIMEOUT = parseInt(process.env.OLLAMA_API_TIMEOUT || "60")
const OLLAMA_MAX_RETRIES = parseInt(process.env.OLLAMA_MAX_RETRIES || "3")
const OLLAMA_RETRY_DELAY = parseInt(process.env.OLLAMA_RETRY_DELAY || "2")

// Define Zod schemas for validation
const AuthorSchema = z
  .string()
  .min(3)
  .refine((author) => / /.test(author), {
    message: "Author name must contain a space",
  })

const PaperMetadataSchema = z.object({
  title: z.string().min(3).max(300),
  authors: z.array(AuthorSchema).min(1),
  field_of_study: z.string().max(200).optional(),
  journal: z.string().max(200).optional(),
  publication_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  doi: z
    .string()
    .regex(/^10\.\d{4,9}\/[\S]+$/)
    .optional(),
  keywords: z.array(z.string()).min(3),
})

// Types inferred from the schemas
type PaperMetadata = z.infer<typeof PaperMetadataSchema>
type Chunk = {
  page_number: number | null
  type: string
  content: string
  chunk_position: number
  current_chapter: string | null
  prev_title?: string
  next_title?: string
}

// Initialize the Ollama client with the configured settings
const ollama = createOllama({
  baseURL: `${OLLAMA_HOST}/api`,
  headers:
    OLLAMA_USERNAME && OLLAMA_PASSWORD
      ? {
          Authorization: `Basic ${Buffer.from(`${OLLAMA_USERNAME}:${OLLAMA_PASSWORD}`).toString("base64")}`,
        }
      : {},
})

// Create models
const chatModel = ollama(OLLAMA_MODEL)
const embeddingModel = ollama.embedding(OLLAMA_EMBEDDING_MODEL)

// Initialize PDF.js
const pdfjsVersion = pdfjsLib.version
console.debug(`Using PDF.js version ${pdfjsVersion}`)

/**
 * Extracts content from a PDF file
 * @param pdfPath Path to the PDF file
 * @param maxContextLength Maximum context length for chunks
 * @returns Array of content chunks
 */
export async function extractPdfContent(pdfPath: string, maxContextLength = 512): Promise<Chunk[]> {
  try {
    // Check if file exists
    await fs.access(pdfPath)

    // Read the PDF file
    const data = await fs.readFile(pdfPath)

    // Load the PDF document
    const pdf = await pdfjsLib.getDocument({ data }).promise
    const numPages = pdf.numPages

    // Process each page
    const content: Chunk[] = []
    let currentChapter: string | null = null
    let prevTitle: string | null = null

    // Basic title detection regex
    const titleRegex = /^(?:[A-Z][A-Za-z0-9\s]{0,50}|\d+\.\s+[A-Z][A-Za-z0-9\s]{0,50})$/

    for (let pageNum = 1; pageNum <= numPages; pageNum++) {
      const page = await pdf.getPage(pageNum)
      const textContent = await page.getTextContent()
      const pageText = textContent.items
        .map((item: any) => ("str" in item ? item.str : ""))
        .join(" ")

      // Split into paragraphs and process
      const paragraphs = pageText.split(/\n\n+/)

      for (let pIndex = 0; pIndex < paragraphs.length; pIndex++) {
        const trimmedParagraph = paragraphs[pIndex].trim()
        if (!trimmedParagraph) continue

        // Simple heuristic to detect titles
        const isTitle = titleRegex.test(trimmedParagraph) && trimmedParagraph.length < 100
        const elementType = isTitle ? "Title" : "Text"

        const chunk: Chunk = {
          page_number: pageNum,
          type: elementType,
          content: trimmedParagraph,
          chunk_position: content.length,
          current_chapter: currentChapter,
        }

        if (isTitle) {
          chunk.prev_title = prevTitle || undefined
          prevTitle = trimmedParagraph
          currentChapter = trimmedParagraph
        }

        content.push(chunk)
      }
    }

    // Set next_title for all titles
    const titleElements = content.filter((item) => item.type === "Title")
    for (let i = 0; i < titleElements.length - 1; i++) {
      titleElements[i].next_title = titleElements[i + 1].content
    }

    if (titleElements.length > 0) {
      titleElements[titleElements.length - 1].next_title = ""
    }

    // Split content into chunks of maxContextLength
    const result: Chunk[] = []
    let currentChunk: string = ""
    let currentMetadata: Omit<Chunk, "content"> | null = null

    for (const item of content) {
      // If adding this item would exceed maxContextLength, push current chunk and start a new one
      if (currentChunk.length + item.content.length > maxContextLength && currentChunk.length > 0) {
        if (currentMetadata) {
          result.push({
            ...currentMetadata,
            content: currentChunk,
          })
        }
        currentChunk = ""
      }

      // If starting a new chunk, use this item's metadata
      if (currentChunk.length === 0) {
        currentMetadata = {
          page_number: item.page_number,
          type: item.type,
          chunk_position: result.length,
          current_chapter: item.current_chapter,
          prev_title: item.prev_title,
          next_title: item.next_title,
        }
      }

      // Add content to current chunk
      currentChunk += (currentChunk ? " " : "") + item.content
    }

    // Add the last chunk if there's anything left
    if (currentChunk.length > 0 && currentMetadata) {
      result.push({
        ...currentMetadata,
        content: currentChunk,
      })
    }

    return result
  } catch (error) {
    console.error(`Error extracting PDF content: ${error}`)
    throw error
  }
}

/**
 * Extracts raw text from a PDF
 * @param pdfPath Path to the PDF file
 * @returns Raw text from the PDF
 */
export async function extractTextFromPdf(pdfPath: string): Promise<string> {
  try {
    // Check if file exists
    await fs.access(pdfPath)

    // Read the PDF file
    const data = await fs.readFile(pdfPath)

    // Load the PDF document
    const pdf = await pdfjsLib.getDocument({ data }).promise
    const numPages = pdf.numPages

    let fullText = ""

    for (let i = 1; i <= numPages; i++) {
      const page = await pdf.getPage(i)
      const textContent = await page.getTextContent()
      const pageText = textContent.items
        .map((item: any) => ("str" in item ? item.str : ""))
        .join(" ")

      fullText += pageText + "\n\n"
    }

    return fullText
  } catch (error) {
    console.error(`Error extracting text from PDF: ${error}`)
    throw error
  }
}

/**
 * Send embedding request to Ollama with retry logic
 * @param inputText Text to embed
 * @returns Embedding vector or null if failed
 */
export async function sendEmbedRequest(inputText: string): Promise<number[] | null> {
  for (let attempt = 0; attempt < OLLAMA_MAX_RETRIES; attempt++) {
    try {
      const response = await embeddingModel.embed(inputText)
      return response
    } catch (error) {
      console.error(
        `Embedding request failed (attempt ${attempt + 1}/${OLLAMA_MAX_RETRIES}): ${error}`,
      )
      if (attempt < OLLAMA_MAX_RETRIES - 1) {
        await new Promise((resolve) => setTimeout(resolve, OLLAMA_RETRY_DELAY * 1000))
      }
    }
  }

  console.error(`Embedding request failed after ${OLLAMA_MAX_RETRIES} attempts.`)
  return null
}

/**
 * Gets embeddings for a PDF paper
 * @param pdfPath Path to the PDF file
 * @returns Object containing embeddings and model info
 */
export async function getPaperEmbeddings(
  pdfPath: string,
): Promise<{ embeddings: number[][]; model_name: string; model_version: string }> {
  try {
    const textContent = await extractPdfContent(pdfPath)

    if (!textContent || textContent.length === 0) {
      console.warn(`No text extracted from PDF: ${pdfPath}`)
      return { embeddings: [], model_name: OLLAMA_EMBEDDING_MODEL, model_version: "1.0" }
    }

    // Get embeddings for each segment
    const embeddings: number[][] = []
    for (const chunk of textContent) {
      const embedding = await sendEmbedRequest(chunk.content)
      if (embedding) {
        embeddings.push(embedding)
      } else {
        console.warn(`Failed to get embedding for segment in ${pdfPath}`)
      }
    }

    return { embeddings, model_name: OLLAMA_EMBEDDING_MODEL, model_version: "1.0" }
  } catch (error) {
    console.error(`Error in getPaperEmbeddings: ${error}`)
    throw error
  }
}

/**
 * Gets embeddings for a query string
 * @param queryString Query to embed
 * @returns Embedding vector
 */
export async function getQueryEmbeddings(queryString: string): Promise<number[] | null> {
  if (!queryString.trim()) {
    throw new Error("Query string cannot be empty.")
  }

  return await sendEmbedRequest(queryString)
}

/**
 * Generate JSON data from the model using a schema
 * @param prompt The prompt to send to the model
 * @param schema Zod schema for validating the response
 * @returns Parsed and validated data
 */
export async function generateStructuredData<T extends z.ZodType>(
  prompt: string,
  schema: T,
): Promise<z.infer<T>> {
  try {
    const response = await chatModel.generate({
      messages: [{ role: "user", content: prompt }],
      response_format: { type: "json_object" },
    })

    let parsedData
    try {
      parsedData = JSON.parse(response.text)
    } catch (error) {
      throw new Error(`Failed to parse JSON response: ${error}`)
    }

    try {
      return schema.parse(parsedData)
    } catch (error) {
      throw new Error(`Data validation failed: ${error}`)
    }
  } catch (error) {
    console.error("Error generating structured data:", error)
    throw error
  }
}

/**
 * Gets metadata for a PDF paper
 * @param filePath Path to the PDF file
 * @returns Paper metadata
 */
export async function getPaperInfo(filePath: string): Promise<PaperMetadata> {
  try {
    // Check if file exists
    await fs.access(filePath)

    // Extract text from the first page
    const firstPageText = await extractFirstPageText(filePath)

    // Generate structured data from the first page
    const prompt = `
      You are a helpful assistant. Extract the metadata from the first page of this academic paper.
      Return only the structured information matching these fields:
      - title: The full title of the paper
      - authors: A list of author names
      - field_of_study: The general research area (e.g., Computer Science, Biology), if identifiable
      - journal: The journal name, if available
      - publication_date: The publication date in ISO format (YYYY-MM-DD)
      - doi: The Digital Object Identifier (DOI), if available
      - keywords: A list of keywords, if listed
      
      Only return fields you can confidently extract from the page — do not guess or fabricate.
      
      Here is the first page of the paper:
      
      ${firstPageText}
    `

    return await generateStructuredData(prompt, PaperMetadataSchema)
  } catch (error) {
    console.error(`Error generating paper info for ${filePath}: ${error}`)
    throw error
  }
}

/**
 * Extract text from just the first page of a PDF
 * @param pdfPath Path to the PDF file
 * @returns Text from the first page
 */
async function extractFirstPageText(pdfPath: string): Promise<string> {
  try {
    // Read the PDF file
    const data = await fs.readFile(pdfPath)

    // Load the PDF document
    const pdf = await pdfjsLib.getDocument({ data }).promise

    // Get the first page
    const page = await pdf.getPage(1)
    const textContent = await page.getTextContent()

    // Extract text from the page
    const pageText = textContent.items.map((item: any) => ("str" in item ? item.str : "")).join(" ")

    return pageText
  } catch (error) {
    console.error(`Error extracting first page text: ${error}`)
    throw error
  }
}

export default {
  getPaperEmbeddings,
  getQueryEmbeddings,
  getPaperInfo,
  extractPdfContent,
  extractTextFromPdf,
  sendEmbedRequest,
}
