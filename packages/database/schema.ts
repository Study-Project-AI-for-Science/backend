import { integer, jsonb, pgTable, text, timestamp, vector } from "drizzle-orm/pg-core"
import { uuidv7 } from "uuidv7"

// Helpers

const timestamps = {
  createdAt: timestamp({ withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp({ withTimezone: true }).notNull().defaultNow(),
  deletedAt: timestamp({ withTimezone: true }),
}

// Tables

export const users = pgTable("users", {
  id: text().primaryKey().$defaultFn(uuidv7),
  name: text().notNull(),
  email: text().notNull().unique(),
  password: text().notNull(),
  ...timestamps,
})

export const sessions = pgTable("sessions", {
  token: text().primaryKey().notNull(),
  userId: text()
    .notNull()
    .references(() => users.id),
  ...timestamps,
})

export const papers = pgTable("papers", {
  id: text().primaryKey().$defaultFn(uuidv7),
  title: text().notNull(),
  authors: text().notNull(),
  fileUrl: text().notNull(),
  fileHash: text().notNull().unique(),
  abstract: text(),
  onlineUrl: text(),
  content: text(),
  publishedDate: timestamp({ withTimezone: true }),
  ...timestamps,
})

export const paperEmbeddings = pgTable("paper_embeddings", {
  id: text().primaryKey().$defaultFn(uuidv7),
  paperId: text()
    .notNull()
    .references(() => papers.id),
  embedding: vector("embedding", { dimensions: 1024 }).notNull(),
  modelName: text().notNull(),
  modelVersion: text().notNull(),
  embeddingHash: text().unique(),
  ...timestamps,
})

export const paperReferences = pgTable("paper_references", {
  id: text().primaryKey().$defaultFn(uuidv7),
  title: text().notNull(),
  authors: text().notNull(),
  fields: jsonb().notNull(),
  paperId: text()
    .notNull()
    .references(() => papers.id),
  referencePaperId: text().references(() => papers.id),
  ...timestamps,
})
