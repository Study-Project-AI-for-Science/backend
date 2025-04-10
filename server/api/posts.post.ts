import { z } from "zod"
import { posts } from "~~/packages/database/schema"

const bodySchema = z.object({
  content: z.string().min(1).max(256),
})

export default defineEventHandler(async (event) => {
  const { secure } = await requireUserSession(event)
  if (!secure) return createError({ statusCode: 401, message: "Unauthorized" })

  const { content } = await readValidatedBody(event, bodySchema.parse)

  // Create new post
  const [post] = await useDrizzle()
    .insert(posts)
    .values({
      content: content,
      userId: secure.userId,
    })
    .returning()

  return post
})
