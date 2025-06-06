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

const BIBITEM_PATTERN =
  /\\bibitem(?:\[(.*?)])?\{(.*?)\}(.*?)(?=\\bibitem|\\end\{thebibliography\}|$)/gs

function parseBibitemContent(body: string): Partial<ReferenceEntry> {
  const rawText = body.replace(/\s+/g, " ").trim()

  /* split on real new lines and newblock */
  const logicalLines = body
    .replace(/\\newblock\s*/gi, "\n")
    .split(/\r?\n+/)
    .map(l => l.trim())
    .filter(Boolean)

  const fields: Partial<ReferenceEntry> = { raw_text: rawText }

  if (logicalLines.length > 0) {
    fields.author = logicalLines[0]?.replace(/\.$/, "")
  }

  if (logicalLines.length > 1) {
    fields.title = logicalLines[1]?.replace(/\.$/, "")
  }

  /* journal heuristics */
  const journalPatterns = [
    /\\textit{([^}]+)}/,
    /\\emph{([^}]+)}/,
    /{\\em\s+([^}]+)}/,
    /\\em\s+([^,\.]+)/,
    /In\s+{\\\w+\s+([^}]+)}/,
    /In\s+\\textit{([^}]+)}/,
    /In\s*["']([^"']+)["']/,
    /(?:In |in ){\\it ([^}]+)}/,
    /(?:\.)\s+([A-Z][^,\.]*(?:Journal|Proceedings|Transactions|Review|Letters)[^,\.]*)/,
  ]
  for (const p of journalPatterns) {
    const m = p.exec(rawText)
    if (m) {
      fields.journal = m[1].trim()
      break
    }
  }

  /* conference / booktitle heuristics */
  if (!fields.journal) {
    const booktitlePatterns = [
      /In\s+(?:proceedings\s+of|proc\.\s+of|Proc\.\s+of)\s+the\s+([^,\.]+)/i,
      /In\s+([^,\.]*(?:Conference|Symposium|Workshop)[^,\.]*)/i,
    ]
    for (const p of booktitlePatterns) {
      const m = p.exec(rawText)
      if (m) {
        fields.booktitle = m[1].trim()
        break
      }
    }
  }

  /* publisher */
  const publisherPatterns = [
    /(?:publisher|Publisher)\s*[:=]\s*([^,\.]+)/,
    /([^,\.]+?(?:Press|Publishers|Publishing))/,
  ]
  for (const p of publisherPatterns) {
    const m = p.exec(rawText)
    if (m) {
      fields.publisher = m[1].trim()
      break
    }
  }

  /* year, volume, number, pages */
  fields.year  = /\b(19|20)\d{2}\b/.exec(rawText)?.[0]
  fields.volume = /(?:volume|Vol\.)\s*[:=]?\s*(\d+)/i.exec(rawText)?.[1]
  fields.number =
    /(?:number|No\.|issue)\s*[:=]?\s*(\d+)/i.exec(rawText)?.[1] ?? undefined
  const pg = /(?:pages|pp\.)\s*[:=]?\s*([\d\-–—]+)/i.exec(rawText)?.[1]
  if (pg) fields.pages = pg.replace(/[–—]/g, "-")

  /* identifiers */
  fields.doi =
    /doi\s*[:=]\s*([^\s,]+)/i.exec(rawText)?.[1] ??
    /https?:\/\/(?:dx\.)?doi\.org\/([^\s,]+)/i.exec(rawText)?.[1]
  fields.url =
    /\\url{([^}]+)}/.exec(rawText)?.[1] ?? /https?:\/\/[^\s,}]+/.exec(rawText)?.[0]
  fields.arxiv =
    /arXiv:([^\s,}]+)/i.exec(rawText)?.[1] ??
    /https?:\/\/arxiv\.org\/abs\/([^\s,}]+)/i.exec(rawText)?.[1]

  /* address/location */
  const addrPatterns = [
    /address\s*[:=]\s*([^,\.]+)/,
    /([A-Z][a-zA-Z]+,\s+[A-Z]{2,})/,
    /([A-Z][a-zA-Z]+,\s+[A-Z][a-zA-Z]+)/,
  ]
  for (const p of addrPatterns) {
    const m = p.exec(rawText)
    if (m) {
      fields.address = m[1].trim()
      break
    }
  }

  /* book heuristic */
  if (/\\textit{[^}]*book[^}]*/i.test(rawText) && !fields.journal)
    fields.type = "book"

  return fields
}

/**
 * LaTeX bibliography parser (handles \bibitem blocks)
 */
function parseLatexBibliographyContent(content: string): ReferenceEntry[] {
  const entries: ReferenceEntry[] = []
  let m
  while ((m = BIBITEM_PATTERN.exec(content)) !== null) {
    const [, optLabel, citeKey, body] = m
    const entry: ReferenceEntry = {
      id: citeKey?.trim() || "",
      type: "bibitem",
      ...(optLabel ? { label: optLabel.trim() } : {}),
      ...parseBibitemContent(body.trim()),
    }
    entry.raw_bibitem = optLabel
      ? `\\bibitem[${optLabel}] {${citeKey}} ${body.trim()}`
      : `\\bibitem{${citeKey}} ${body.trim()}`
    entries.push(entry)
  }
  return entries
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

  // If no BibTeX files found, check LaTeX files for \bibitem blocks
  if (!foundBibtex) {
    const texFiles = await findFiles(paperDir, ".tex")
    let foundAny = false

    for (const filePath of texFiles) {
      try {
        const content = await fs.readFile(filePath, "utf-8")

        if (content.includes("\\bibitem")) {
          const entries = parseLatexBibliographyContent(content)
          entries.forEach(e => (entriesMap[e.id] = e))
          if (entries.length) foundAny = true
          console.log(
            `Parsed ${entries.length} entries from LaTeX file: ${filePath}`,
          )
        }
      } catch (error) {
        console.error(
          `Error reading LaTeX file ${filePath}: ${
            error instanceof Error ? error.message : String(error)
          }`,
        )
      }
    }

    if (!foundAny) {
      console.warn(`No bibliography sources found in ${paperDir}`)
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
