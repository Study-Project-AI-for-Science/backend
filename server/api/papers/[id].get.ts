import { defineEventHandler, getRouterParam, createError } from "h3"
import { paperFind } from "~~/packages/database/db" // Corrected import path

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id")

  if (!id) {
    throw createError({
      statusCode: 400,
      statusMessage: "Missing paper ID",
    })
  }

  try {
    const paper = await paperFind(id)

    if (!paper || Object.keys(paper).length === 0) {
      // Check if paper exists
      throw createError({
        statusCode: 404,
        statusMessage: "Paper not found",
      })
    }

    return paper
  } catch (error: any) {
    // Handle potential errors from paperFind or if it throws for not found
    if (error.statusCode === 404) {
      throw error // Re-throw the 404 error
    }
    console.error(`Error fetching paper ${id}:`, error)
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to fetch paper: ${error.message || "Unknown error"}`,
    })
  }
})
