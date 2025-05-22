import { drizzle } from "drizzle-orm/postgres-js"
import * as schema from "~~/packages/database/schema"
import postgres from "postgres"

const client = postgres(process.env.POSTGRES_URL!)

const db = drizzle({ client, schema, casing: "snake_case" })

export function useDrizzle() {
  return db
}
