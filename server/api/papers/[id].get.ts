import { papers } from "~~/packages/database/schema"
import { eq } from "drizzle-orm"
import { z } from "zod"

const routeParams = z.object({
  id: z.string(),
})

export default defineEventHandler(async (event) => {
  const { id } = await getValidatedRouterParams(event, routeParams.parse)

  const [paper] = await useDrizzle().select().from(papers).where(eq(papers.id, id)).limit(1)
  if (!paper) throw createError({ statusCode: 404, statusMessage: "Paper not found" })
  return paper
})
