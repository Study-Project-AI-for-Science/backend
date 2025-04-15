import { createHash } from "crypto"
import { createReadStream } from "fs"
import { papers, paperEmbeddings, paperReferences } from "./schema"
import { eq, desc, count, like, sql, gt, cosineDistance} from "drizzle-orm"
import { extractArxivIds, downloadArxivPaper, paperDownloadArxivId } from "../retriever/arxivUtils"; 
import { join } from "path";
import * as storage from "../storage/storage"
import { generateEmbedding, getPaperInfo, getPaperEmbeddings, extractTextFromPdf, extractReferencesFromFile } from "../ollama/ollamaUtils"; // Assuming an embedding generation function exists
import { parseLatexToMarkdown, extractReferences } from "../latexParser/latexUtils"
import { useDrizzle } from "../../server/utils/drizzle";


// Define the input type for a reference based on the example
export interface ReferenceInput {
  id: string // Citation key
  title: string
  authors: string
  raw_bibtex: string
  [key: string]: any // Allow additional fields like booktitle, year, etc.
}


/**
 * Computes a SHA-256 hash of a file
 * @param filepath The path to the file
 * @returns Promise that resolves to the hex string hash
 */
export async function paperComputeFileHash(filepath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const fileStream = createReadStream(filepath)
    const hash = createHash("sha256")

    fileStream.on("data", (data) => {
      hash.update(data)
    })

    fileStream.on("end", () => {
      resolve(hash.digest("hex"))
    })

    fileStream.on("error", (error) => {
      reject(error)
    })
  })
}

export async function paperFind(paperId: string): Promise<Record<string, any>> {
  const paper = await useDrizzle().select().from(papers).where(eq(papers.id, paperId)).limit(1)
  // Assuming the query returns a single paper object
  return paper[0] || {}
}

export async function paperGetFile(paperId: string, destinationPath: string): Promise<void> {
  try {
    // 1. Find the paper record to get the file URL
    const paper = await paperFind(paperId);
    if (!paper || !paper.storageUrl) {
      // Assuming the paper object has a 'storageUrl' property
      throw new Error(`Paper with ID ${paperId} not found or does not have a storage URL.`);
    }

    // 2. Use the storage download function
    const fileUrl = paper.storageUrl;
    console.log(`Downloading file from ${fileUrl} to ${destinationPath}`);
    await storage.downloadFile(fileUrl, destinationPath);
    console.log(`Successfully downloaded file for paper ${paperId} to ${destinationPath}`);

  } catch (error) {
    console.error(`Error getting file for paper ${paperId}:`, error);
    // Re-throw the error or handle it as needed
    throw error;
  }
}

export async function paperGetEmbeddings(paperId: string): Promise<Record<string, any> | null> {
  /**
   * Retrieves embeddings for a specific paper from the database.
   *
   * @param paperId The unique identifier of the paper.
   * @returns A promise that resolves to the embedding object or null if not found.
   * @throws Error if a database error occurs during query execution.
   */
  try {

    const result = await useDrizzle()
      .select() // Select all columns from the embeddings table for this paper
      .from(paperEmbeddings) // Assuming an 'embeddings' table schema exists
      .where(eq(paperEmbeddings.paperId, paperId)) // Assuming 'embeddings' table has a 'paperId' foreign key

    if (result.length >= 0) {
      return result; 
    } else {
      console.log(`Embeddings not found for paper ${paperId}.`);
      return null; // Return null if no embeddings are found
    }
  } catch (error) {
    console.error(`Database error retrieving embeddings for paper ${paperId}:`, error);
    // Consider throwing a custom DatabaseError
    throw error; // Re-throw the caught error
  }
}

// TODO: There needs to be a way, that if the user uplaods a paper, that is already in the database, but there aren't any references yet that the pipeline to download the references, etc. is triggered.
/**
   * Inserts a paper into the database and handles file upload and metadata extraction.
   *
   * @param filePath The path to the paper file.
   * @param title The title of the paper.
   * @param authors The authors of the paper.
   * @param abstract The abstract of the paper (optional).
   * @param paperUrl The URL of the paper (optional).
   * @param published The published date of the paper (optional).
   * @param updated The updated date of the paper (optional).
   * @param markdownContent The markdown content of the paper (optional).
   * @param processReferences Flag to indicate if references should be processed (default: true).
   * @returns A promise that resolves to the ID of the inserted paper.
   */
export async function paperInsert(
  filePath: string,
  title: string,
  authors: string,
  abstract?: string,
  paperUrl?: string,
  published?: string,
  updated?: string,
  markdownContent?: string, // Assuming this might be used for embedding or reference extraction later
  processReferences: boolean = true,
): Promise<string> {
  
  try {
    // 1. Compute File Hash
    const fileHash = await paperComputeFileHash(filePath);
    console.log(`Computed hash for ${filePath}: ${fileHash}`);

    // Optional: Check if a paper with this hash already exists to prevent duplicates
    const existingPaper = await useDrizzle().select({ id: papers.id }).from(papers).where(eq(papers.fileHash, fileHash)).limit(1);
    if (existingPaper.length > 0) {
      console.log(`Paper at ${filePath} already exists with ID: ${existingPaper[0]!.id}. Skipping insertion.`);
      // TODO: Trigger reference processing if needed for existing paper (as per the TODO above the function)

      return existingPaper[0]!.id;
    }

    // 2. Upload to S3
    // Assuming storage(filePath) is the upload function returning the URL
    const storageUrl = await storage.uploadFile(filePath);
    console.log(`Uploaded ${filePath} to ${storageUrl}`);


    if (!title || !authors) {
      const info = await getPaperInfo(filePath);
      title = title || info.title || "Untitled Paper";
      authors = authors || info.authors || "Unknown Authors";
      abstract = abstract || info.abstract || undefined;
    }

    const arxivIds = await extractArxivIds(paperUrl || "");
    let arxivId: string | undefined = undefined;
    if (arxivIds.length > 0) {
      arxivId = arxivIds[0]; // Use the first found ArXiv ID
      console.log(`Found ArXiv ID: ${arxivId}`);
      await paperDownloadArxivId(arxivId!, "/var/tmp/arxiv_papers");
      const sourceDir = join("/var/tmp/arxiv_papers", arxivId!.replace(".", ""));
      if (!markdownContent) {
        markdownContent = await parseLatexToMarkdown(sourceDir);
      }
    } else {
      console.log("No ArXiv ID found.");
    }

    if (!markdownContent) {
      markdownContent = await extractTextFromPdf(filePath);
    }
    
    // 3. Insert Paper Metadata into "papers" table
    const paperData = {
      title: title,
      authors: authors,
      abstract: abstract,
      onlineUrl: paperUrl,
      fileUrl: storageUrl,
      fileHash: fileHash,
      // Convert string dates to Date objects if they exist
      publishedDate: published ? new Date(published) : undefined,
      updatedDate: updated ? new Date(updated) : undefined,
      content: markdownContent
    };

    const insertedPaperResult = await useDrizzle()
      .insert(papers)
      .values(paperData)
      .returning({ insertedId: papers.id });

    if (!insertedPaperResult || insertedPaperResult.length === 0 || !insertedPaperResult[0]?.insertedId) {
        throw new Error("Failed to insert paper metadata or retrieve its ID.");
    }
    const paperId = insertedPaperResult[0].insertedId;
    console.log(`Inserted paper metadata with ID: ${paperId}`);


    // 4. Generate Embeddings (Example: Embed abstract or title)

    try {
    
      const embeddingInfo = await getPaperEmbeddings(filePath);
      const embeddingsList = embeddingInfo.embeddings || [Array(1024).fill(0.0)]; // Ensure it's an array
      const modelName = embeddingInfo.modelName || undefined;
      const modelVersion = embeddingInfo.modelVersion || undefined;

      // Prepare data for bulk insertion
      const embeddingsToInsert = embeddingsList.map((embedding: number[]) => ({
        paperId: paperId,
        embedding: embedding,
        modelName: modelName || "",
        modelVersion: modelVersion || "",
      }));

      // 5. Insert Embeddings into "paper_embeddings" table
      if (embeddingsToInsert.length > 0) {
        await useDrizzle()
          .insert(paperEmbeddings)
          .values(embeddingsToInsert);
        console.log(`Inserted ${embeddingsToInsert.length} embeddings for paper ID: ${paperId}`);
      } else {
        console.warn(`No embeddings generated or found for paper ID: ${paperId}`);
      }
      console.log(`Inserted embedding for paper ID: ${paperId}`);
    } catch (embeddingError) {
      console.error(`Failed to generate or insert embedding for paper ${paperId}:`, embeddingError);
      // Decide if this error is critical. Maybe log and continue?
      // For now, we'll let the main try/catch handle it.
      throw embeddingError;
    }

    // 6. Handle References (Optional)
    if (processReferences) {
      console.log(`Processing references for paper ${paperId}...`);
      if (arxivId) {
        const sourceDir = join("/var/tmp/arxiv_papers", arxivId!.replace(".", ""));
        const rawReferences: Record<string, any>[] = await extractReferences(sourceDir);

        // Map the raw references to the ReferenceInput interface
        const extractedReferences: ReferenceInput[] = rawReferences.map((rawRef): ReferenceInput => {
            const mappedRef: ReferenceInput = {
          // Spread rawRef to include all original fields first
          ...rawRef,
          // Explicitly map/override required fields, ensuring they are strings
          id: String(rawRef.ID || rawRef.id),
          title: String(rawRef.title || 'Untitled Reference'), // Default title if none found
          authors: String(rawRef.author || 'Unknown Author(s)'), // Default author if none found
          raw_bibtex: String(rawRef.raw || rawRef.raw_bibtex || ''), // Default empty string if none found
            };
            return mappedRef;
        });

        if (extractedReferences && extractedReferences.length > 0) {
          await paperReferencesInsertMany(paperId, extractedReferences);
        }
        
      } else {
        const extractedReferences: ReferenceInput[] = await extractReferencesFromFile(filePath);
        if (extractedReferences && extractedReferences.length > 0) {
          await paperReferencesInsertMany(paperId, extractedReferences);
        } else {
          console.log(`No references found or extracted for paper ${paperId}.`);
        }
      }
    }
    // 7. Return Paper ID
    return paperId;
  } catch (error) {
    console.error(`Error inserting paper ${filePath}:`, error);
    // Optionally, re-throw the error for higher-level handling
    if (error instanceof Error) {
      throw new Error(`Failed to insert paper: ${error.message}`);
    } else {
      throw new Error(`Failed to insert paper: ${String(error)}`);
    }
  }

}

/**
 * Retrieves papers similar to the given query string based on their embeddings.
 *
 * @param query The query string to find similar papers.
 * @param limit The maximum number of similar papers to return.
 * @param similarityDropout Minimum similarity score threshold (default: 0.0).
 * @returns A promise that resolves to an array of similar papers with their similarity scores.
 */
export async function paperGetSimilarToQuery(
  query: string,
  limit: number = 10,
  /**
   * Minimum similarity score threshold. Papers with similarity strictly greater
   * than this value will be returned. Assumes similarity is in a range where
   * higher means more similar (e.g., 0 to 1 for cosine similarity).
   */
  similarityDropout: number = 0.0,
): Promise<Array<Record<string, any> & { similarity: number }>> {

  try {
    // 1. Generate embedding for the input query string
    const queryEmbedding = await generateEmbedding(query);
    if (!queryEmbedding || queryEmbedding.length === 0) {
      console.error("Failed to generate embedding for query or embedding is empty:", query);
      // Return empty array if embedding generation fails or is empty
      return [];
    }

    // 2. Define the similarity calculation using SQL for pgvector cosine similarity
    //    The <=> operator in pgvector calculates cosine distance (0=identical, 1=orthogonal, 2=opposite).
    //    Cosine Similarity = 1 - Cosine Distance.
    //    The queryEmbedding (number[]) is converted to a string format '[1,2,3]' suitable for pgvector.
    // const similarity = sql<number>`1 - (${paperEmbeddings.embedding} <=> ${JSON.stringify(queryEmbedding)})`.as("similarity");
    const similarity = sql<number>`1 - (${cosineDistance(paperEmbeddings.embedding, queryEmbedding)})`;

    // 3. Query the database for similar paper embeddings
    const results = await useDrizzle()
      .select({
        // Select all columns from the papers table
        paper: papers,
        // Select the calculated similarity score
        similarity: similarity,
      })
      .from(paperEmbeddings)
      // Join with the papers table to get paper details
      .innerJoin(papers, eq(paperEmbeddings.paperId, papers.id))
      // Filter results based on the minimum similarity threshold
      .where(gt(similarity, similarityDropout))
      // Order by similarity in descending order (most similar first)
      .orderBy(desc(similarity))
      // Limit the number of results
      .limit(limit);

    // 4. Format and return the results
    return results.map(result => ({
      ...result.paper, // Spread the paper data
      similarity: result.similarity, // Add the similarity score
    }));

  } catch (error) {
    console.error("Error getting similar papers:", error);
    // Return an empty array in case of error during the database query or processing
    return [];
    // Optionally, re-throw the error if the caller should handle it:
    // throw new Error(`Failed to retrieve similar papers: ${error.message}`);
  }
}

export async function paperUpdate(paperId: string, updates: { [key: string]: any }): Promise<void> {
  await useDrizzle()
    .update(papers)
    .set(updates)
    .where(eq(papers.id, paperId))
    .returning()
    .then((result) => {
      console.log("Updated paper:", result)
    })
    .catch((error) => {
      console.error("Error updating paper:", error)
    })
}

export async function paperDelete(paperId: string): Promise<void> {
  const db = useDrizzle(); // Get the Drizzle instance

  try {
    // Wrap all database operations in a transaction
    await db.transaction(async (tx) => {
      // 1. Delete associated embeddings
      await tx.delete(paperEmbeddings).where(eq(paperEmbeddings.paperId, paperId));
      console.log(`Deleted embeddings for paper ${paperId}`);

      // 2. Delete references originating FROM this paper
      await tx.delete(paperReferences).where(eq(paperReferences.paperId, paperId));
      console.log(`Deleted references originating from paper ${paperId}`);

      // 3. Nullify references pointing TO this paper
      // Check if referencePaperId exists before updating
      const referencesToUpdate = await tx.select({ id: paperReferences.id })
                                        .from(paperReferences)
                                        .where(eq(paperReferences.referencePaperId, paperId));

      if (referencesToUpdate.length > 0) {
        await tx.update(paperReferences)
          .set({ referencePaperId: null }) // Set referencePaperId to null
          .where(eq(paperReferences.referencePaperId, paperId));
        console.log(`Nullified ${referencesToUpdate.length} references pointing to paper ${paperId}`);
      } else {
        console.log(`No references found pointing to paper ${paperId}.`);
      }


      // 4. Delete the paper itself and get the fileUrl
      const deletedPaperResult = await tx.delete(papers)
        .where(eq(papers.id, paperId))
        .returning({ fileUrl: papers.fileUrl }); // Only return the fileUrl

      if (deletedPaperResult.length === 0) {
        // If the paper wasn't found, throw an error to rollback the transaction
        throw new Error(`Paper with ID ${paperId} not found for deletion.`);
      }
      console.log(`Deleted paper record ${paperId}`);

      // 5. Handle file deletion (contingent on transaction success)
      // This part is outside the transaction block but relies on its successful completion
      const fileUrlToDelete = deletedPaperResult[0]?.fileUrl;
      if (fileUrlToDelete) {
        // Perform file deletion asynchronously after transaction commits
        // We don't await this, as the primary goal is DB consistency.
        // Log errors if file deletion fails.
        storage.deleteFile(fileUrlToDelete).catch(err => {
            console.error(`Error deleting file ${fileUrlToDelete} from storage:`, err);
        });
        console.log(`Initiated deletion of storage file: ${fileUrlToDelete}`);
      } else {
        console.warn(`File URL not found for deleted paper ${paperId}. Storage file not deleted.`);
      }
    }); // Transaction commits here if no errors were thrown

    console.log(`Successfully deleted paper ${paperId} and associated data.`);

  } catch (error) {
    console.error(`Error during deletion process for paper ${paperId}:`, error);
    // Re-throw the error to signal failure to the caller
    throw error;
  }
}

export async function paperListPaginated(
  page: number = 1,
  pageSize: number = 10,
): Promise<{ papers: Record<string, any>[]; total: number }> {
  const offset = (page - 1) * pageSize
  const retrievedPapers = await useDrizzle()
    .select()
    .from(papers)
    .limit(pageSize)
    .offset(offset)
    .orderBy(desc(papers.createdAt))

  const total = await useDrizzle()
    .select({ count: count(papers.id) })
    .from(papers)
  return {
    papers: retrievedPapers,
    total: total[0]?.count || 0,
  }
}

export async function paperFindByArxivId(arxivId: string): Promise<Record<string, any> | null> {
  /**
   * Finds a paper in the database where the onlineUrl contains the given ArXiv ID.
   *
   * @param arxivId The ArXiv ID string to search for within the onlineUrl.
   * @returns A promise that resolves to the paper object if found, otherwise null.
   */
  try {
    const result = await useDrizzle()
      .select() // Select all columns
      .from(papers)
      // Use 'like' for substring matching. Ensure 'onlineUrl' is the correct column name.
      .where(like(papers.onlineUrl, `%${arxivId}%`))
      .limit(1); // Get only the first match

    return result[0] || null; // Return the first paper found, or null if no results
  } catch (error) {
    console.error(`Error finding paper by ArXiv ID (${arxivId}):`, error);
    // Consider throwing a custom DatabaseError
    throw error; // Re-throw the caught error
  }
}
// References

export async function paperReferencesInsertMany(
  paperId: string,
  references: ReferenceInput[],
): Promise<number> {

  if (!references || references.length === 0) {
    console.warn("No references provided to insert.")
    // throw new Error("References list cannot be empty."); // Or a custom ValueError
    return 0
  }

  // Optional: Check if the paper with paperId exists
  const mainPaper = await useDrizzle()
    .select({ id: papers.id })
    .from(papers)
    .where(eq(papers.id, paperId))
    .limit(1)
  if (mainPaper.length === 0) {
    console.error(`Paper with ID ${paperId} not found.`)
    throw new Error(`Paper with ID ${paperId} not found.`) // Or a custom PaperNotFoundError
  }

  // Process each reference to find/insert ArXiv papers and get their IDs
  const valuesToInsertPromises = references.map(async (ref) => {
    // TODO: Consider a more robust temporary directory strategy
    const referencedPaperId = await processReferenceWithArxivId(ref, "/tmp/ref_papers");

    // Separate known fields from the rest to store in 'fields'
    const { id, type, title, authors, raw_bibtex, ...otherFields } = ref;

    return {
      paperId: paperId, // The ID of the paper containing this reference list
      referenceKey: id, // The citation key (e.g., "turbo")
      referencePaperId: referencedPaperId, // ID of the referenced paper if found on ArXiv, otherwise null
      rawBibtex: raw_bibtex,
      title: title,
      authors: authors, // Map input 'authors' to schema 'authors'
      fields: otherFields, // Store remaining fields as JSON
      // Potentially map other specific fields if needed, e.g., type: type
    };
  });

  // Wait for all reference processing to complete
  const valuesToInsert = await Promise.all(valuesToInsertPromises);


  try {
    // Assuming paperReferences is the Drizzle schema object for the join table
    const result = await useDrizzle()
      .insert(paperReferences)
      .values(valuesToInsert)
      .returning({ insertedId: paperReferences.id }) // Return inserted IDs or count

    console.log(`Successfully inserted ${result.length} references for paper ${paperId}.`)
    return result.length
  } catch (error) {
    console.error(`Database error inserting references for paper ${paperId}:`, error)
    // Consider throwing a custom DatabaseError
    throw error // Re-throw the caught error
  }
}

export async function paperReferencesList(paperId: string): Promise<Record<string, any>[]> {
  /**
   * Retrieves all references for a specific paper from the database.
   * Queries the "paper_references" table to find all papers that are referenced
   * by the paper with the given `paperId`.
   *
   * @param paperId The unique identifier of the paper.
   * @returns A promise that resolves to a list of reference objects.
   * @throws Error if a database error occurs during query execution.
   */
  try {
    const references = await useDrizzle()
      .select()
      .from(paperReferences)
      .where(eq(paperReferences.paperId, paperId))

    return references
  } catch (error) {
    console.error(`Database error retrieving references for paper ${paperId}:`, error)
    // Consider throwing a custom DatabaseError or PaperNotFoundError if appropriate
    throw error // Re-throw the caught error
  }
}

/**
 * Process a reference that contains an ArXiv ID by downloading and adding it to the system.
 *
 * Description:
 *     Extracts ArXiv IDs from the reference metadata, downloads the paper if an ID is found,
 *     and inserts it into the database using the standard paper_insert process.
 *
 * Parameters:
 *     reference (Record<string, any>): A dictionary containing reference metadata potentially including ArXiv IDs in fields like 'eprint'.
 *     tempDir (string): A temporary directory where the referenced paper will be downloaded.
 *
 * Returns:
 *     Promise<string | null>: The paper_id of the newly inserted paper if successful, null otherwise.
 *
 * Example:
 *     const paperId = await processReferenceWithArxivId(reference, "/tmp/ref_papers");
 */
export async function processReferenceWithArxivId(
  reference: Record<string, any>,
  tempDir: string,
): Promise<string | null> {

  try {
    // Search through all keys and values in the reference object for ArXiv IDs
    let arxivIds: string[] = [];
    const extractionPromises: Promise<string[]>[] = [];

    for (const [key, value] of Object.entries(reference)) {
      // Check key (always a string in Record<string, any>)
      extractionPromises.push(extractArxivIds(key));

      // Check value if it's a string
      if (typeof value === 'string') {
      extractionPromises.push(extractArxivIds(value));
      }
    }

    // Wait for all extraction calls to complete
    const results = await Promise.all(extractionPromises);

    // Flatten the array of arrays and remove duplicates
    arxivIds = Array.from(new Set(results.flat()));

    if (!arxivIds || arxivIds.length === 0) {
      console.log("No ArXiv ID found in reference.");
      return null;
    }

    // Use the first found ArXiv ID
    const arxivId: string = arxivIds[0]!; // Add '!' to assert non-null
    console.log(`Found ArXiv ID: ${arxivId}. Attempting download...`);

    // Check if paper already exists by ArXiv ID
    const existingPaper = await paperFindByArxivId(arxivId);
    if (existingPaper) {
        console.log(`Paper with ArXiv ID ${arxivId} already exists with ID: ${existingPaper.id}`);
        return existingPaper.id;
    }


    // Download the paper
    const downloadedFilePath = await downloadArxivPaper(arxivId, tempDir); // Assumes this function downloads and returns the path
    if (!downloadedFilePath) {
        console.error(`Failed to download paper for ArXiv ID: ${arxivId}`);
        return null;
    }
    console.log(`Paper downloaded to: ${downloadedFilePath}`);


    // TODO: Use existing python stuff to get the metadata
    // Prepare metadata for insertion (using data from reference as fallback)
    // Ideally, metadata would be extracted from the downloaded paper itself
    const title = reference.title || `Paper ${arxivId}`;
    const authors = reference.author || "Unknown Authors"; // Map 'author' field if available
    const abstract = reference.abstract || undefined; // Optional
    const paperUrl = `https://arxiv.org/abs/${arxivId}`; // Construct ArXiv URL
    const published = reference.year || undefined; // Use 'year' field if available

    // Insert the downloaded paper into the database
    // Note: paperInsert currently returns void. We need a way to get the ID.
    // Option 1: Modify paperInsert to return the ID.
    // Option 2: Query for the paper after insertion using a unique identifier (like ArXiv ID or file hash).
    // We'll proceed assuming Option 2 is possible via paperFindByArxivId.
    const paperId = await paperInsert(
        downloadedFilePath,
        title,
        authors,
        abstract,
        paperUrl,
        published,
        undefined, // updated
        undefined, // markdownContent - might be generated later
        false, // withReferences - set to false to avoid immediate reference processing
        // Add arxivId to the insert function if the schema supports it directly
        // Or handle it via paperUpdate after insertion if needed
    );
    if (!paperId) {
        console.error(`Failed to insert paper with ArXiv ID ${arxivId}`);
        return null;
    }
    return paperId; // Return the ID of the newly inserted paper

  } catch (error) {
    console.error("Error processing reference with ArXiv ID:", error);
    // Consider more specific error handling or re-throwing
    return null;
  }
}

