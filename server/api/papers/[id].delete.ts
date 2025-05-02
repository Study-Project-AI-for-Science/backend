import { paperDelete } from "~~/packages/database/db"
import { z } from "zod"

const routeParams = z.object({
  id: z.string(),
})

// Example: Delete a paper by ID
export default defineEventHandler(async (event) => {
  const { id } = await getValidatedRouterParams(event, routeParams.parse)

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
