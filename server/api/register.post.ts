import { users } from "~~/packages/database/schema"
import { eq } from "drizzle-orm"
import { z } from "zod"
import { readValidatedBody, createError } from "h3"
import { useDrizzle } from "../utils/drizzle"

const bodySchema = z.object({
  name: z.string(),
  email: z.string().email(),
  password: z.string().min(8).max(256),
})

export default defineEventHandler(async (event) => {
  const body = await readValidatedBody(event, bodySchema.parse)

  const [existing] = await useDrizzle()
    .select()
    .from(users)
    .where(eq(users.email, body.email))
    .limit(1)

  if (existing) {
    throw createError({ statusCode: 400, message: "Email already in use" })
  }

  const passwordHash = await hashPassword(body.password)

  const [user] = await useDrizzle()
    .insert(users)
    .values({ name: body.name, email: body.email, password: passwordHash })
    .returning()

  if (!user) {
    throw createError({ statusCode: 400, message: "Failed to create user" })
  }

  return { ok: true }
})
