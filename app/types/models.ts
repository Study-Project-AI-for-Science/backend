import type { papers, users } from "~~/server/database/schema"

export type DPaper = typeof papers.$inferSelect
export type DUser = typeof users.$inferSelect
