import { papers } from "~~/packages/database/schema"
import { count, desc } from "drizzle-orm"
import { z } from "zod"

// TODO need to implement the query string and then get the closest vectors/papers to that query

const querySchema = z.object({
  page: z.coerce.number().min(1).optional().default(1),
  pageSize: z.coerce.number().min(1).max(1000).optional().default(10),
})

export default defineEventHandler(async (event) => {
  const { page, pageSize } = await readValidatedBody(event, querySchema.parse)

  const offset = (page - 1) * pageSize

  const paperQuery = await useDrizzle()
    .select()
    .from(papers)
    .offset(offset)
    .orderBy(desc(papers.createdAt))
    .limit(pageSize)

  const totalQuery = await useDrizzle()
    .select({ count: count(papers.id) })
    .from(papers)

  // Fetch simultaneously
  const [retrievedPapers, [total]] = await Promise.all([paperQuery, totalQuery])

  return {
    papers: retrievedPapers,
    total: total?.count || 0,
  }
})
