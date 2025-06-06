import * as fs from "fs/promises"
import * as path from "path"
import { exec } from "child_process"
import { promisify } from "util"

// Promisify exec for async/await usage
const execAsync = promisify(exec)

// Simple interface for reference entries
interface ReferenceEntry {
  id: string
  type: string
  author?: string
  title?: string
  journal?: string
  booktitle?: string
  publisher?: string
  year?: string
  volume?: string
  number?: string
  pages?: string
  doi?: string
  url?: string
  arxiv?: string
  raw_text?: string
  [key: string]: any // Allow for additional fields
}

/**
 * Find all files matching a pattern in a directory and its subdirectories
 */
async function findFiles(directory: string, extension: string): Promise<string[]> {
  try {
    const entries = await fs.readdir(directory, { withFileTypes: true })

    const files = await Promise.all(
      entries.map(async (entry) => {
        const fullPath = path.join(directory, entry.name)

        if (entry.isDirectory()) {
          return findFiles(fullPath, extension)
        } else if (entry.name.endsWith(extension)) {
          return [fullPath]
        } else {
          return []
        }
      }),
    )

    return files.flat()
  } catch (error) {
    console.error(`Error finding files: ${error instanceof Error ? error.message : String(error)}`)
    return []
  }
}

/**
 * Find the main .tex file in a directory by looking for \begin{document}
 */
async function findMainTexFile(directory: string): Promise<string | null> {
  const texFiles = await findFiles(directory, ".tex")

  for (const filePath of texFiles) {
    try {
      const content = await fs.readFile(filePath, { encoding: "utf-8" })

      if (content.includes("\\begin{document}")) {
        console.log(`Found main tex file: ${filePath}`)
        return filePath
      }
    } catch (error) {
      console.warn(
        `Error reading file ${filePath}: ${error instanceof Error ? error.message : String(error)}`,
      )
    }
  }

  console.warn(`No main tex file found in directory: ${directory}`)
  return null
}

/**
 * Parse LaTeX content to Markdown using Pandoc
 */
async function parseLatexToMarkdown(filePath: string): Promise<string> {
  try {
    // Check if input is a directory
    const stats = await fs.stat(filePath)

    if (stats.isDirectory()) {
      const mainFile = await findMainTexFile(filePath)
      if (!mainFile) {
        throw new Error(`No main tex file found in directory: ${filePath}`)
      }
      filePath = mainFile
    }

    // Get directory of the input file
    const workingDir = path.dirname(filePath)
    const fileName = path.basename(filePath)

    // Execute pandoc command
    const { stdout } = await execAsync(
      `pandoc -f latex -t markdown "${fileName}"`,
      { cwd: workingDir }
    )
    return stdout

  } catch (error) {
    throw new Error(
      `LaTeX to Markdown conversion failed: ${error instanceof Error ? error.message : String(error)}`,
    )
  }
}

/**
 * Parse BibTeX content to extract reference entries
 */
function parseBibtexContent(content: string): ReferenceEntry[] {
  const entries: ReferenceEntry[] = []
  const bibtexEntryPattern = /@(\w+)\s*{\s*([^,]+),\s*([^@]+?)(?=\s*@|\s*\Z)/gs
  const bibtexFieldPattern =
    /(\w+)\s*=\s*{((?:[^{}]|{(?:[^{}]|{[^{}]*})*})*)}|(\w+)\s*=\s*"([^"]*)"|(\w+)\s*=\s*(\d+(?:\.\d+)?)|(\w+)\s*=\s*([^,\s{}"'\n]+)/gs

  let match
  while ((match = bibtexEntryPattern.exec(content)) !== null) {
    const entryType = match[1].toLowerCase()
    const entryId = match[2].trim()
    const entryContent = match[3].trim()

    const entry: ReferenceEntry = {
      id: entryId,
      type: entryType,
    }

    // Extract fields
    let fieldMatch
    while ((fieldMatch = bibtexFieldPattern.exec(entryContent)) !== null) {
      let fieldName, fieldValue

      if (fieldMatch[1]) {
        // {...} format
        fieldName = fieldMatch[1].toLowerCase()
        fieldValue = cleanBibtexValue(fieldMatch[2])
      } else if (fieldMatch[3]) {
        // "..." format
        fieldName = fieldMatch[3].toLowerCase()
        fieldValue = cleanBibtexValue(fieldMatch[4])
      } else if (fieldMatch[5]) {
        // numeric format
        fieldName = fieldMatch[5].toLowerCase()
        fieldValue = fieldMatch[6]
      } else if (fieldMatch[7]) {
        // plain text format
        fieldName = fieldMatch[7].toLowerCase()
        fieldValue = fieldMatch[8]
      } else {
        continue
      }

      entry[fieldName] = fieldValue
    }

    entry.raw_bibtex = `@${entryType}{${entryId}, ${entryContent}}`
    entries.push(entry)
  }

  return entries
}

/**
 * Clean BibTeX field values (simplified version)
 */
function cleanBibtexValue(value: string): string {
  if (!value) return value

  // Common LaTeX escape sequences
  const replacements: [RegExp, string][] = [
    [/\\&/g, "&"],
    [
      /\\\"[aouiAOUI]/g,
      (match) => {
        const char = match.charAt(2).toLowerCase()
        return char === "a" ? "ä" : char === "o" ? "ö" : char === "u" ? "ü" : "ï"
      },
    ],
    [
      /\\'{[eEaAoOuUiI]}/g,
      (match) => {
        const char = match.charAt(3).toLowerCase()
        return char === "e"
          ? "é"
          : char === "a"
            ? "á"
            : char === "o"
              ? "ó"
              : char === "u"
                ? "ú"
                : "í"
      },
    ],
    [/\$([^$]+)\$/g, "$1"], // Remove math mode delimiters
    [/{([^{}]*)}/g, "$1"], // Remove unnecessary braces
  ]

  // Apply all replacements
  for (const [pattern, replacement] of replacements) {
    value = value.replace(pattern, replacement)
  }

  return value.replace(/\s+/g, " ").trim()
}

/**
 * Extract references from a paper directory
 */
async function extractReferences(paperDir: string): Promise<ReferenceEntry[]> {
  const allEntries: ReferenceEntry[] = []
  const entriesMap: Record<string, ReferenceEntry> = {}

  // First check BibTeX files
  const bibFiles = await findFiles(paperDir, ".bib")
  let foundBibtex = false

  for (const filePath of bibFiles) {
    try {
      const content = await fs.readFile(filePath, { encoding: "utf-8" })
      const entries = parseBibtexContent(content)

      for (const entry of entries) {
        entriesMap[entry.id] = entry
      }

      console.log(`Parsed ${entries.length} entries from BibTeX file: ${filePath}`)
      foundBibtex = true
    } catch (error) {
      console.error(
        `Error reading BibTeX file ${filePath}: ${error instanceof Error ? error.message : String(error)}`,
      )
    }
  }

  // If no BibTeX files found, try TeX files with bibliography sections
  if (!foundBibtex) {
    const texFiles = await findFiles(paperDir, ".tex")

    for (const filePath of texFiles) {
      try {
        const content = await fs.readFile(filePath, { encoding: "utf-8" })

        if (content.includes("\\bibitem") || content.includes("\\begin{thebibliography}")) {
          // Here we would insert a simplified bibliography parser
          console.log(`Found bibliography in LaTeX file: ${filePath}`)
          // Simplified bibliography parsing would go here
        }
      } catch (error) {
        console.error(
          `Error reading LaTeX file ${filePath}: ${error instanceof Error ? error.message : String(error)}`,
        )
      }
    }
  }

  return Object.values(entriesMap)
}

export { findMainTexFile, parseLatexToMarkdown, extractReferences }

export default {
  parseLatexToMarkdown,
  extractReferences,
  findMainTexFile,
}
