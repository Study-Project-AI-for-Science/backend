import { drizzle } from "drizzle-orm/postgres-js"
import * as schema from "~~/packages/database/schema"
import postgres from "postgres"

console.log("DATABASE_URL at runtime:", process.env.DATABASE_URL) // <-- Add this line

const client = postgres(process.env.DATABASE_URL!)

const db = drizzle({ client, schema, casing: "snake_case" })

export function useDrizzle() {
  return db
}
