import { defineEventHandler, readBody, createError } from 'h3'
import { paperInsert } from '../../../packages/database/db' // Adjust the import path as necessary

export default defineEventHandler(async (event) => {
    const body = await readBody(event)

    // Basic validation for required fields
    if (!body || !body.filePath || !body.title || !body.authors) {
        throw createError({
            statusCode: 400,
            statusMessage: 'Missing required fields: filePath, title, and authors are required.',
        });
    }

    const {
        filePath,
        title,
        authors,
        abstract,
        paperUrl,
        published,
        updated,
        markdownContent,
        processReferences = true, // Default to true if not provided
    } = body;

    try {
        const paperId = await paperInsert(
            filePath,
            title,
            authors,
            abstract,
            paperUrl,
            published,
            updated,
            markdownContent,
            processReferences,
        );

        // Set status code to 201 (Created)
        event.node.res.statusCode = 201;

        return {
            success: true,
            message: 'Paper created successfully.',
            paperId: paperId,
        }
    } catch (error: any) {
        console.error(`Error creating paper:`, error);
        // Handle potential errors, e.g., file not found at filePath, database errors
        throw createError({
            statusCode: 500,
            statusMessage: `Failed to create paper: ${error.message || 'Unknown error'}`,
        });
    }
})
