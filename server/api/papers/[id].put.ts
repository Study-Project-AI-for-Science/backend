import { papers } from "~~/packages/database/schema"
import { eq } from "drizzle-orm"
import { z } from "zod"

const routeParams = z.object({
  id: z.string(),
})

const bodySchema = z.object({
  title: z.string().optional(),
  authors: z.string().optional(),
  abstract: z.string().optional(),
  paperUrl: z.string().optional(),
  published: z.string().optional(),
  updated: z.string().optional(),
  markdownContent: z.string().optional(),
})

export default defineEventHandler(async (event) => {
  const { id } = await getValidatedRouterParams(event, routeParams.parse)
  const body = await readValidatedBody(event, bodySchema.parse)

  const [updatedPaper] = await useDrizzle()
    .update(papers)
    .set(body)
    .where(eq(papers.id, id))
    .returning()

  return updatedPaper
})
