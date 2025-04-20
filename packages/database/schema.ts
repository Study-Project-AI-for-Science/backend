import { integer, jsonb, pgTable, text, timestamp, vector } from "drizzle-orm/pg-core"
import { uuidv7 } from "uuidv7"

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
  updatedDate: timestamp({ withTimezone: true }),
  createdAt: timestamp({ withTimezone: true }).notNull().defaultNow(),
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
  createdAt: timestamp({ withTimezone: true }).notNull().defaultNow(),
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
  createdAt: timestamp({ withTimezone: true }).notNull().defaultNow(),
})

export const users = pgTable("users", {
  id: integer().primaryKey().generatedAlwaysAsIdentity(),
  name: text().notNull(),
  email: text().notNull().unique(),
  password: text().notNull(),
  createdAt: timestamp({ withTimezone: true }).notNull().defaultNow(),
})

export const sessions = pgTable("sessions", {
  token: text().primaryKey().notNull(),
  userId: integer()
    .notNull()
    .references(() => users.id),
  createdAt: timestamp({ withTimezone: true }).notNull().defaultNow(),
})
