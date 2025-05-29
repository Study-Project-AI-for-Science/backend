import { paperReferences } from "~~/packages/database/schema"
import { eq } from "drizzle-orm"
import { z } from "zod"

const routeParams = z.object({
  id: z.string(),
})

export default defineEventHandler(async (event) => {
  const { id } = await getValidatedRouterParams(event, routeParams.parse)

  const references = await useDrizzle()
    .select()
    .from(paperReferences)
    .where(eq(paperReferences.paperId, id))

  return references
})
