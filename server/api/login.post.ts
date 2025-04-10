import { sessions, users } from "~~/packages/database/schema"
import { eq } from "drizzle-orm"
import { z } from "zod"
import { nanoid } from "nanoid"

const bodySchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).max(256),
})

export default defineEventHandler(async (event) => {
  const body = await readValidatedBody(event, bodySchema.parse)

  const [user] = await useDrizzle().select().from(users).where(eq(users.email, body.email)).limit(1)
  if (!user) return createError({ statusCode: 401, message: "Invalid email or password" })

  // Check password hash
  const passwordHash = await verifyPassword(user.password, body.password)
  if (!passwordHash) return createError({ statusCode: 401, message: "Invalid email or password" })

  // Create new session
  const [session] = await useDrizzle()
    .insert(sessions)
    .values({
      token: nanoid(64),
      userId: user.id,
    })
    .returning()

  // Set session cookie
  await setUserSession(event, {
    user: {
      id: user.id,
      name: user.name,
    },
    secure: {
      userId: user.id,
      sessionToken: session.token,
    },
  })

  return {}
})
