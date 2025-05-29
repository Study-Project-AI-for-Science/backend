import { papers } from "~~/packages/database/schema"
import { count, desc, or, ilike, sql } from "drizzle-orm"
import { z } from "zod"

const querySchema = z.object({
  page: z.coerce.number().min(1).optional().default(1),
  pageSize: z.coerce.number().min(1).max(1000).optional().default(10),
  search: z.string().optional(), // TODO need to implement the query string and then get the closest vectors/papers to that query
})

export default defineEventHandler(async (event) => {
  const { page, pageSize, search } = await getValidatedQuery(event, querySchema.parse)

  const offset = (page - 1) * pageSize

  if (search && search.trim()) {
    // If we have a search query, use relevance-based ranking
    const searchTerm = search.trim()
    const searchPattern = `%${searchTerm}%`

    // Calculate relevance score based on:
    // - Title exact match (highest priority: 1000 points)
    // - Title starts with term (very high priority: 500 points)
    // - Title contains full term (high priority: 200 points)
    // - Title contains partial match (medium priority: 50 points)
    // - Authors contains term (medium priority: 30 points)
    // - Abstract contains term (low priority: 10 points)
    // - Multiple occurrences get bonus points
    const relevanceScore = sql`
      CASE 
        WHEN LOWER(${papers.title}) = LOWER(${searchTerm}) THEN 1000
        WHEN LOWER(${papers.title}) LIKE LOWER(${searchTerm} || '%') THEN 500
        WHEN LOWER(${papers.title}) LIKE LOWER('%' || ${searchTerm} || '%') THEN 200
        ELSE 0
      END +
      CASE 
        WHEN LOWER(${papers.authors}) LIKE LOWER('%' || ${searchTerm} || '%') THEN 30
        ELSE 0
      END +
      CASE 
        WHEN LOWER(${papers.abstract}) LIKE LOWER('%' || ${searchTerm} || '%') THEN 10
        ELSE 0
      END +
      -- Bonus for multiple occurrences in abstract (up to 5 extra points per occurrence)
      GREATEST(0, LEAST(50, (LENGTH(LOWER(${papers.abstract})) - LENGTH(REPLACE(LOWER(${papers.abstract}), LOWER(${searchTerm}), ''))) / LENGTH(${searchTerm}) * 5))
    `.as("relevance_score")

    // Search condition
    const searchCondition = or(
      ilike(papers.title, searchPattern),
      ilike(papers.authors, searchPattern),
      ilike(papers.abstract, searchPattern),
    )

    // Get papers with relevance scoring
    const paperResults = await useDrizzle()
      .select({
        id: papers.id,
        title: papers.title,
        authors: papers.authors,
        abstract: papers.abstract,
        fileHash: papers.fileHash,
        fileUrl: papers.fileUrl,
        onlineUrl: papers.onlineUrl,
        content: papers.content,
        createdAt: papers.createdAt,
        updatedAt: papers.updatedAt,
        deletedAt: papers.deletedAt,
        publishedDate: papers.publishedDate,
        relevanceScore,
      })
      .from(papers)
      .where(searchCondition)
      .orderBy(desc(relevanceScore), desc(papers.createdAt))
      .offset(offset)
      .limit(pageSize)

    // Get total count for pagination
    const [total] = await useDrizzle()
      .select({ count: count(papers.id) })
      .from(papers)
      .where(searchCondition)

    if (!total) throw createError({ statusCode: 500, statusMessage: "Failed to get total count" })

    // Remove the relevance score from the response (internal use only)
    const cleanResults = paperResults.map(({ relevanceScore, ...paper }) => {
      // Optional: Log relevance scores for debugging
      console.log(`Paper "${paper.title}" - Relevance Score: ${relevanceScore}`)
      return paper
    })

    return {
      papers: cleanResults,
      total: total?.count || 0,
    }
  } else {
    // No search query, return papers ordered by creation date
    const paperResults = await useDrizzle()
      .select()
      .from(papers)
      .offset(offset)
      .orderBy(desc(papers.createdAt))
      .limit(pageSize)

    const [total] = await useDrizzle()
      .select({ count: count(papers.id) })
      .from(papers)

    if (!total) throw createError({ statusCode: 500, statusMessage: "Failed to get total count" })

    return {
      papers: paperResults,
      total: total?.count || 0,
    }
  }
})
