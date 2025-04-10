import { integer, jsonb, pgTable, text, timestamp, vector } from "drizzle-orm/pg-core"
import { uuidv7 } from "uuidv7"
export const papers = pgTable("papers", {
  id: integer().primaryKey().$defaultfn(uuidv7),
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

export const paperEmbeddings = pgTable("paperEmbeddings", {
  id: uuid("id").primaryKey().default(sql`uuid_generate_v7()`).notNull(),
  paperId: uuid("paperId").notNull().references(() => papers.id),
  embedding: vector("embedding", { dimensions: 1024 }).notNull(),
  modelName: text().notNull(),
  modelVersion: text().notNull(),
  embeddingHash: text().notNull().unique(),
  createdAt: timestamp({ withTimezone: true }).notNull().defaultNow(),
})

export const paperReferences = pgTable("paperReferences", {
  id: uuid("id").primaryKey().default(sql`uuid_generate_v7()`).notNull(),
  title: text().notNull(),
  authors: text().notNull(),
  fields: jsonb().notNull(),
  paperId: uuid("paperId").notNull().references(() => papers.id),
  referencePaperId: uuid("referencePaperId").notNull().references(() => papers.id),
  createdAt: timestamp({ withTimezone: true }).notNull().defaultNow(),
})
