import { drizzle } from "drizzle-orm/postgres-js"
import * as schema from "~~/packages/database/schema"
import postgres from "postgres"


const POSTGRES_URL = process.env.POSTGRES_URL!
console.log("POSTGRES_URL:", POSTGRES_URL)
const client = postgres(POSTGRES_URL)

const db = drizzle({ client, schema, casing: "snake_case" })

export function useDrizzle() {
  return db
}
