


export async function extractArxivIds(text:string): Promise<string[]> {
    // Matches the pattern dddd.ddddd
    const arxivIdRegex = /\d{4}\.\d{5}/g;
    const matches = text.match(arxivIdRegex);
    // Return the matches found, or an empty array if none were found.
    return matches ? matches : [];
}

export async function downloadArxivPaper(arxivId: string, tempDir: string): Promise<string> {
    // TODO - Implement the logic to download the paper from arXiv using the arxivId
    // This is a placeholder implementation.
    return "";
}

export async function paperDownloadArxivId(arxivId: string, tempDir: string): Promise<string> {
    // TODO - Implement the logic to download the paper from arXiv using the arxivId
    // This is a placeholder implementation.
    return "";
}