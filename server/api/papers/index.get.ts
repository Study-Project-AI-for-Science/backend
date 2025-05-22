import { papers } from "~~/packages/database/schema"
import { count, desc } from "drizzle-orm"
import { z } from "zod"

const querySchema = z.object({
  page: z.coerce.number().min(1).optional().default(1),
  pageSize: z.coerce.number().min(1).max(1000).optional().default(10),
  search: z.string().optional(), // TODO need to implement the query string and then get the closest vectors/papers to that query
})

export default defineEventHandler(async (event) => {
  const { page, pageSize } = await getValidatedQuery(event, querySchema.parse)

  const offset = (page - 1) * pageSize

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
})
