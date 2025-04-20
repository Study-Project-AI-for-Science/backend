import { defineEventHandler, getQuery, createError } from "h3"
import { paperListPaginated } from "../../../packages/database/db" // Adjust the import path as necessary

// TODO need to implement the query string and then get the closest vectors/papers to that query

export default defineEventHandler(async (event) => {
  const query = getQuery(event)

  // Default values for pagination
  let page = 1
  let pageSize = 10

  // Parse and validate page number
  if (query.page) {
    const parsedPage = parseInt(query.page as string, 10)
    if (!isNaN(parsedPage) && parsedPage > 0) {
      page = parsedPage
    } else {
      throw createError({
        statusCode: 400,
        statusMessage: "Invalid page number. Page must be a positive integer.",
      })
    }
  }

  // Parse and validate page size
  if (query.pageSize) {
    const parsedPageSize = parseInt(query.pageSize as string, 10)
    // Add reasonable limits for pageSize if needed, e.g., max 100
    if (!isNaN(parsedPageSize) && parsedPageSize > 0) {
      pageSize = parsedPageSize
    } else {
      throw createError({
        statusCode: 400,
        statusMessage: "Invalid page size. Page size must be a positive integer.",
      })
    }
  }

  try {
    const result = await paperListPaginated(page, pageSize)
    return result // Contains { papers: [], total: number }
  } catch (error: any) {
    console.error(`Error fetching paginated papers (page: ${page}, pageSize: ${pageSize}):`, error)
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to fetch papers: ${error.message || "Unknown error"}`,
    })
  }
})
