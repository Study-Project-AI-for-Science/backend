import { defineEventHandler, getRouterParam, createError } from "h3"
import { paperDelete } from "~~/packages/database/db" // Corrected import path

// Example: Delete a paper by ID
export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id")

  if (!id) {
    throw createError({
      statusCode: 400,
      statusMessage: "Missing paper ID",
    })
  }

  try {
    await paperDelete(id)
    return {
      success: true,
      message: `Paper with id ${id} deleted successfully.`,
    }
  } catch (error: any) {
    console.error(`Error deleting paper ${id}:`, error)
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to delete paper: ${error.message || "Unknown error"}`,
    })
  }
})
