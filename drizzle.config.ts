import { defineConfig } from "drizzle-kit"

export default defineConfig({
  out: "./packages/database/migrations",
  schema: "./packages/database/schema.ts",
  dialect: "postgresql",
  casing: "snake_case",
  dbCredentials: {
    url: process.env.POSTGRES_URL!,
  },
})
