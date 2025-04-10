import { posts } from "~~/packages/database/schema"
import { desc } from "drizzle-orm"

export default defineEventHandler(async (event) => {
  const { secure } = await requireUserSession(event)
  if (!secure) return createError({ statusCode: 401, message: "Unauthorized" })

  // Create new post
  const result = await useDrizzle().select().from(posts).orderBy(desc(posts.createdAt))

  return result
})
