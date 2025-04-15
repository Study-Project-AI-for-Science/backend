import { defineEventHandler, getRouterParam, createError } from 'h3'
import { paperReferencesList } from '~~/packages/database/db' // Corrected import path

export default defineEventHandler(async (event) => {
    const id = getRouterParam(event, "id")

    if (!id) {
        throw createError({
            statusCode: 400,
            statusMessage: 'Missing paper ID',
        });
    }

    try {
        const references = await paperReferencesList(id);
        // paperReferencesList likely returns an empty array if the paper has no references or doesn't exist.
        // No explicit 404 check needed here unless the underlying function throws one.
        return references;
    } catch (error: any) {
        console.error(`Error fetching references for paper ${id}:`, error);
        // Handle potential errors from paperReferencesList
        throw createError({
            statusCode: 500,
            statusMessage: `Failed to fetch references: ${error.message || 'Unknown error'}`,
        });
    }
})
