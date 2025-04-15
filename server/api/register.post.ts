// import { users } from "~~/packages/database/schema"
// import { eq } from "drizzle-orm"
// import { z } from "zod"

// const bodySchema = z.object({
//   name: z.string(),
//   email: z.string().email(),
//   password: z.string().min(8).max(256),
// })

// export default defineEventHandler(async (event) => {
//   const body = await readValidatedBody(event, bodySchema.parse)

//   const passwordHash = await hashPassword(body.password)

//   // Create new user
//   const [user] = await useDrizzle()
//     .insert(users)
//     .values({
//       name: body.name,
//       email: body.email,
//       password: passwordHash,
//     })
//     .returning()
//   if (!user) return createError({ statusCode: 400, message: "Failed to create user" })

//   return {}
// })
