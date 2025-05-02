import * as fs from "fs/promises"
import * as path from "path"
import { createWriteStream } from "fs"
import * as tar from "tar"
import * as stream from "stream"
import { promisify } from "util"
import { z } from "zod"

// Define schemas with Zod
const AuthorSchema = z.object({
  name: z.string(),
})

const ArxivResultSchema = z.object({
  title: z.string(),
  authors: z.array(AuthorSchema),
  summary: z.string(),
  entry_id: z.string(),
  published: z.date(),
  updated: z.date(),
})

const PaperMetadataSchema = z.object({
  title: z.string(),
  authors: z.string(),
  abstract: z.string(),
  url: z.string(),
  arxiv_id: z.string(),
  published_date: z.date(),
  updated_date: z.date(),
})

// Infer TypeScript types from Zod schemas
type Author = z.infer<typeof AuthorSchema>
type ArxivResult = z.infer<typeof ArxivResultSchema>
type PaperMetadata = z.infer<typeof PaperMetadataSchema>

// Utility functions
const pipeline = promisify(stream.pipeline)

async function fileDownload(url: string, outputPath: string): Promise<void> {
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`Failed to download: ${response.status} ${response.statusText}`)
  }

  const fileStream = createWriteStream(outputPath)

  if (!response.body) {
    throw new Error("Response body is null")
  }

  await pipeline(response.body as unknown as stream.Readable, fileStream)
}

async function tarGzExtract(filePath: string, outputDir: string): Promise<string> {
  console.debug(`Extracting ${filePath} to ${outputDir}`)

  try {
    await tar.extract({
      file: filePath,
      cwd: outputDir,
    })

    console.info(`Successfully extracted ${filePath} to ${outputDir}`)
    return outputDir
  } catch (e) {
    const error = e as Error
    console.error(`Error extracting ${filePath}: ${error.message}`)
    throw new Error(`Error extracting ${filePath}: ${error.message}`)
  }
}

// ArXiv API functions
async function arxivSearchById(arxivId: string): Promise<ArxivResult | null> {
  console.debug(`Searching for paper with arXiv ID: ${arxivId}`)

  try {
    const url = `http://export.arxiv.org/api/query?id_list=${arxivId}`
    const response = await fetch(url)

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`)
    }

    const data = await response.text()
    const results = arxivParseResponse(data)

    if (results.length > 0) {
      console.info(`Found paper with arXiv ID: ${arxivId}`)

      // Validate with Zod schema
      try {
        return ArxivResultSchema.parse(results[0])
      } catch (validationError) {
        console.error("Schema validation failed:", validationError)
        throw new Error(`Invalid data structure returned from arXiv API for ID ${arxivId}`)
      }
    } else {
      console.warn(`No paper found with arXiv ID: ${arxivId}`)
      return null
    }
  } catch (e) {
    const error = e as Error
    console.error(`Error searching arXiv ID ${arxivId}: ${error.message}`)
    throw new Error(`Error searching arXiv ID ${arxivId}: ${error.message}`)
  }
}

async function arxivSearchByMetadata(authors: string, title: string): Promise<ArxivResult | null> {
  console.debug(`Searching for paper with title: ${title} and authors: ${authors}`)

  try {
    const filters = []

    if (authors) {
      filters.push(`au:${authors}`)
    }

    if (title) {
      filters.push(`ti:${title}`)
    }

    const query = filters.join(" AND ")
    const url = `http://export.arxiv.org/api/query?search_query=${encodeURIComponent(query)}&max_results=1&sortBy=relevance&sortOrder=descending`
    const response = await fetch(url)

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`)
    }

    const data = await response.text()
    const results = arxivParseResponse(data)

    if (results.length > 0) {
      console.info("Found paper matching metadata search")

      // Validate with Zod schema
      try {
        return ArxivResultSchema.parse(results[0])
      } catch (validationError) {
        console.error("Schema validation failed:", validationError)
        throw new Error(`Invalid data structure returned from arXiv API for metadata search`)
      }
    } else {
      console.warn("No paper found matching metadata search")
      return null
    }
  } catch (e) {
    const error = e as Error
    console.error(`Error searching arXiv with metadata: ${error.message}`)
    throw new Error(`Error searching arXiv with metadata: ${error.message}`)
  }
}

async function arxivSearchAll(query: string, maxResults: number): Promise<ArxivResult[]> {
  console.debug(`Performing general search with query: ${query}, max_results: ${maxResults}`)

  try {
    const url = `http://export.arxiv.org/api/query?search_query=${encodeURIComponent(query)}&max_results=${maxResults}&sortBy=relevance&sortOrder=descending`
    const response = await fetch(url)

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`)
    }

    const data = await response.text()
    const results = arxivParseResponse(data)

    // Validate each result with Zod schema
    const validatedResults: ArxivResult[] = []
    for (let i = 0; i < results.length; i++) {
      try {
        validatedResults.push(ArxivResultSchema.parse(results[i]))
      } catch (validationError) {
        console.warn(`Skipping invalid result at index ${i}:`, validationError)
      }
    }

    return validatedResults
  } catch (e) {
    const error = e as Error
    console.error(`Error searching arXiv with query '${query}': ${error.message}`)
    throw new Error(`Error searching arXiv with query '${query}': ${error.message}`)
  }
}

function arxivParseResponse(xmlData: string): any[] {
  // This is a simplified parser
  // In a production environment, use a proper XML parser like fast-xml-parser
  const entries: any[] = []

  // Extract entries
  const entryRegex = /<entry>([\s\S]*?)<\/entry>/g
  let match

  while ((match = entryRegex.exec(xmlData)) !== null) {
    const entryContent = match[1]

    // Extract fields
    const title = xmlExtractField(entryContent, "title")
    const summary = xmlExtractField(entryContent, "summary")
    const id = xmlExtractField(entryContent, "id")
    const published = new Date(xmlExtractField(entryContent, "published"))
    const updated = new Date(xmlExtractField(entryContent, "updated"))

    // Extract authors
    const authors: Author[] = []
    const authorRegex = /<author>([\s\S]*?)<\/author>/g
    let authorMatch

    while ((authorMatch = authorRegex.exec(entryContent)) !== null) {
      const authorContent = authorMatch[1]
      const name = xmlExtractField(authorContent, "name")
      authors.push({ name })
    }

    entries.push({
      title,
      authors,
      summary,
      entry_id: id,
      published,
      updated,
    })
  }

  return entries
}

function xmlExtractField(content: string, fieldName: string): string {
  const regex = new RegExp(`<${fieldName}[^>]*>([\s\S]*?)<\/${fieldName}>`, "i")
  const match = content.match(regex)
  return match ? match[1].trim() : ""
}

function arxivGetShortId(entryId: string): string {
  // Extract the short ID from the full entry_id
  const match = entryId.match(/arxiv\.org\/abs\/(.+)$/)
  return match ? match[1] : entryId
}

async function arxivDownloadPDF(paper: ArxivResult, outputDir: string): Promise<string> {
  const shortId = arxivGetShortId(paper.entry_id)
  const pdfUrl = `https://arxiv.org/pdf/${shortId}.pdf`
  const outputPath = path.join(outputDir, `${shortId}.pdf`)

  try {
    await fileDownload(pdfUrl, outputPath)
    return outputPath
  } catch (e) {
    const error = e as Error
    throw new Error(`Error downloading PDF: ${error.message}`)
  }
}

async function arxivDownloadSource(paper: ArxivResult, outputDir: string): Promise<string> {
  const shortId = arxivGetShortId(paper.entry_id)
  const sourceUrl = `https://arxiv.org/e-print/${shortId}`
  const outputPath = path.join(outputDir, `${shortId}.tar.gz`)

  try {
    await fileDownload(sourceUrl, outputPath)
    return outputPath
  } catch (e) {
    const error = e as Error
    throw new Error(`Error downloading source: ${error.message}`)
  }
}

function arxivGetMetadata(paper: ArxivResult): PaperMetadata {
  let authorsStr = ""
  for (let i = 0; i < paper.authors.length; i++) {
    authorsStr += paper.authors[i].name
    if (i < paper.authors.length - 1) {
      authorsStr += ", "
    }
  }

  const shortId = arxivGetShortId(paper.entry_id)

  const metadata = {
    title: paper.title,
    authors: authorsStr,
    abstract: paper.summary,
    url: paper.entry_id,
    arxiv_id: shortId,
    published_date: paper.published,
    updated_date: paper.updated,
  }

  // Validate with Zod schema
  try {
    return PaperMetadataSchema.parse(metadata)
  } catch (validationError) {
    console.error("Metadata schema validation failed:", validationError)
    throw new Error("Failed to create valid paper metadata")
  }
}

// Helper functions
function arxivExtractIds(text: string): string[] {
  const pattern = /\d{4}\.\d{5}/g
  const matches = text.matchAll(pattern)
  const ids: string[] = []

  for (const match of matches) {
    ids.push(match[0])
  }

  return ids
}

async function pdfGetText(filePath: string, pageNum = 0): Promise<string> {
  // This is a placeholder. In a real implementation, you'd use a PDF parsing library
  // like pdf-parse or pdfjs-dist
  try {
    // Simulating getting text from a PDF
    return `This is PDF text extracted from ${filePath} at page ${pageNum}`
  } catch (e) {
    const error = e as Error
    throw new Error(`Error extracting text from PDF: ${error.message}`)
  }
}

// Main exported functions
export async function paperGetMetadata(filePath: string): Promise<Partial<PaperMetadata>> {
  console.debug(`Attempting to extract metadata from ${filePath}`)

  // Try to find arxiv ID in filename
  const arxivIds = arxivExtractIds(filePath)
  if (arxivIds.length > 0) {
    console.debug(`Found arXiv ID in filename: ${arxivIds[0]}`)

    try {
      const paper = await arxivSearchById(arxivIds[0])
      if (paper) {
        console.info("Successfully retrieved metadata using arXiv ID from filename")
        return arxivGetMetadata(paper)
      }
    } catch (error) {
      console.warn("Failed to retrieve metadata using arXiv ID from filename")
    }
  }

  // Try to find paper using filename
  console.debug("Attempting to find paper using filename")
  try {
    const fileName = path.basename(filePath, path.extname(filePath))
    const results = await arxivSearchAll(fileName, 15)

    for (let i = 0; i < results.length; i++) {
      if (filePath.includes(results[i].title)) {
        console.info("Successfully retrieved metadata using filename search")
        return arxivGetMetadata(results[i])
      }
    }
  } catch (error) {
    console.warn("Failed to retrieve metadata using filename search")
  }

  // Try to find arxiv ID in PDF content
  console.debug("Attempting to find arXiv ID in PDF content")
  try {
    const text = await pdfGetText(filePath)
    const arxivIdsFromText = arxivExtractIds(text)

    if (arxivIdsFromText.length > 0) {
      console.debug(`Found arXiv ID in PDF content: ${arxivIdsFromText[0]}`)

      try {
        const paper = await arxivSearchById(arxivIdsFromText[0])
        if (paper) {
          console.info("Successfully retrieved metadata using arXiv ID from PDF content")
          return arxivGetMetadata(paper)
        }
      } catch (error) {
        console.warn("Failed to retrieve metadata using arXiv ID from PDF content")
      }
    }
  } catch (e) {
    const error = e as Error
    const errorMsg = `Error extracting information from PDF ${filePath}: ${error.message}`
    console.error(errorMsg)
  }

  console.warn(`Could not extract metadata from ${filePath}`)
  // Return an empty object that conforms to the partial schema
  return {}
}

export async function paperDownloadArxivId(arxivId: string, outputDir: string): Promise<string> {
  console.debug(`Attempting to download paper with ID ${arxivId} to ${outputDir}`)

  const paper = await arxivSearchById(arxivId)
  if (!paper) {
    console.error(`Paper with ID ${arxivId} not found`)
    throw new Error(`Paper with ID ${arxivId} not found`)
  }

  const paperPath = await arxivDownloadPaper(paper, outputDir)
  console.info(`Successfully downloaded paper ${arxivId} to ${paperPath}`)
  return paperPath
}

export async function paperDownloadArxivMetadata(
  authors = "",
  title = "",
  outputDir = ".",
): Promise<string> {
  console.debug(`Attempting to download paper with title '${title}' by ${authors}`)

  // Escape special characters
  const safeTitle = title.replace(/:/g, "\\:").replace(/-/g, "\\-")

  const paper = await arxivSearchByMetadata(authors, safeTitle)
  if (!paper) {
    const errorMsg = `Paper with title '${title}' by ${authors} not found`
    console.error(errorMsg)
    throw new Error(errorMsg)
  }

  const paperPath = await arxivDownloadPaper(paper, outputDir)
  if (!paperPath) {
    const errorMsg = `Error downloading paper with title '${title}'`
    console.error(errorMsg)
    throw new Error(errorMsg)
  }

  console.info(`Successfully downloaded paper to ${paperPath}`)
  return paperPath
}

async function arxivDownloadPaper(paper: ArxivResult, outputDir: string): Promise<string> {
  console.debug(`Attempting to download paper ${paper.title} to ${outputDir}`)

  try {
    // Ensure output directory exists
    await fs.mkdir(outputDir, { recursive: true })

    // Download PDF
    const pdfPath = await arxivDownloadPDF(paper, outputDir)

    // Download source
    try {
      const sourcePath = await arxivDownloadSource(paper, outputDir)
      const extractDir = path.join(outputDir, path.basename(pdfPath, ".pdf"))

      // Extract source if it's a tar.gz file
      if (sourcePath.endsWith(".tar.gz")) {
        try {
          await tarGzExtract(sourcePath, extractDir)
          await fs.unlink(sourcePath)
          console.info(`Deleted archive file ${sourcePath}`)
        } catch (e) {
          const error = e as Error
          console.warn(`Failed to extract or delete archive file: ${error.message}`)
        }
      }
    } catch (e) {
      const error = e as Error
      console.warn(`Failed to download source: ${error.message}`)
    }

    console.info(`Successfully downloaded paper ${paper.entry_id} to ${pdfPath}`)
    return pdfPath
  } catch (e) {
    const error = e as Error
    console.error(`Error downloading paper: ${error.message}`)
    throw new Error(`Error downloading paper: ${error.message}`)
  }
}
