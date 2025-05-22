import { paperEmbeddings, paperReferences, papers } from "~~/packages/database/schema"
import { eq } from "drizzle-orm"
import { z } from "zod"

const routeParams = z.object({
  id: z.string(),
})

export default defineEventHandler(async (event) => {
  const { id: paperId } = await getValidatedRouterParams(event, routeParams.parse)

  await useDrizzle().transaction(async (tx) => {
    await tx.delete(paperEmbeddings).where(eq(paperEmbeddings.paperId, paperId))
    await tx.delete(paperReferences).where(eq(paperReferences.paperId, paperId))

    // 3. Nullify references pointing TO this paper
    const referencesToUpdate = await tx
      .select({ id: paperReferences.id })
      .from(paperReferences)
      .where(eq(paperReferences.referencePaperId, paperId))

    if (referencesToUpdate.length > 0) {
      await tx
        .update(paperReferences)
        .set({ referencePaperId: null })
        .where(eq(paperReferences.referencePaperId, paperId))
      console.log(`Nullified ${referencesToUpdate.length} references pointing to paper ${paperId}`)
    } else {
      console.log(`No references found pointing to paper ${paperId}.`)
    }

    // 4. Delete the paper itself and get the fileUrl
    const [deletedPaperResult] = await tx
      .delete(papers)
      .where(eq(papers.id, paperId))
      .returning({ fileUrl: papers.fileUrl })

    if (!deletedPaperResult) throw new Error(`Paper with ID ${paperId} not found for deletion.`)

    // TODO: storage.deleteFile(fileUrlToDelete)
  })

  return {}
})
