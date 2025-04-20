import { defineEventHandler, getRouterParam, readBody, createError } from "h3"
import { paperUpdate } from "~~/packages/database/db" // Corrected import path

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id")
  const updates = await readBody(event)

  if (!id) {
    throw createError({
      statusCode: 400,
      statusMessage: "Missing paper ID",
    })
  }

  if (!updates || Object.keys(updates).length === 0) {
    throw createError({
      statusCode: 400,
      statusMessage: "Missing update data in request body",
    })
  }

  try {
    await paperUpdate(id, updates)
    return {
      success: true,
      message: `Paper with id ${id} updated successfully.`,
    }
  } catch (error: any) {
    console.error(`Error updating paper ${id}:`, error)
    // Consider adding specific error handling for "not found" if paperUpdate provides it
    throw createError({
      statusCode: 500, // Or 404 if the error indicates the paper wasn't found
      statusMessage: `Failed to update paper: ${error.message || "Unknown error"}`,
    })
  }
})
