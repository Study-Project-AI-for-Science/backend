import { useState } from "react";
import type { Route } from "./+types/home";

export function meta({}: Route.MetaArgs) {
  return [{ title: "New React Router App" }, { name: "description", content: "Welcome to React Router!" }];
}

export default function Home() {
  const [paragraph, setParagraph] = useState("");
  const [reference, setReference] = useState("");
  const [result, setResult] = useState<{
    similarity: number;
    matches: string[];
  } | null>(null);

  const compareTexts = () => {
    const similarity = calculateSimilarity(paragraph, reference);
    const matches = findMatches(paragraph, reference);

    setResult({
      similarity,
      matches,
    });
  };

  return (
    <div className="container mx-auto max-w-2xl p-8">
      <div className="overflow-hidden rounded-lg bg-white shadow">
        <div className="p-6">
          <h1 className="mb-6 text-3xl font-bold">Text Comparison Tool</h1>

          <div className="space-y-6">
            <div className="space-y-2">
              <label className="block text-xl text-gray-600">Paragraph from Paper</label>
              <textarea
                value={paragraph}
                onChange={(e) => setParagraph(e.target.value)}
                placeholder="Enter the paragraph from your paper..."
                className="min-h-[120px] w-full resize-none rounded-lg border border-gray-200 px-3 py-2 text-gray-700 focus:border-transparent focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div className="space-y-2">
              <label className="block text-xl text-gray-600">Reference</label>
              <textarea
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder="Enter the reference text..."
                className="min-h-[120px] w-full resize-none rounded-lg border border-gray-200 px-3 py-2 text-gray-700 focus:border-transparent focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <button
              onClick={compareTexts}
              type="button"
              className="w-full rounded-md bg-blue-600 px-3.5 py-2.5 text-sm font-semibold text-white shadow-xs hover:bg-blue-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
            >
              Compare Texts
            </button>

            {result && (
              <div className="space-y-4 pt-4">
                <h2 className="text-2xl font-bold">Comparison Result</h2>
                <p className="text-xl">Similarity: {result.similarity.toFixed(2)}%</p>
                {result.matches.length > 0 && (
                  <>
                    <h3 className="text-xl font-bold">Matches:</h3>
                    <ul className="list-disc space-y-2 pl-6">
                      {result.matches.map((match, index) => (
                        <li key={index} className="text-lg">
                          {match}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function calculateSimilarity(str1: string, str2: string): number {
  const longer = str1.length > str2.length ? str1 : str2;
  const shorter = str1.length > str2.length ? str2 : str1;

  if (longer.length === 0) return 100;

  const editDistance = levenshteinDistance(longer, shorter);
  return (1 - editDistance / longer.length) * 100;
}

function levenshteinDistance(str1: string, str2: string): number {
  const matrix = Array(str2.length + 1)
    .fill(null)
    .map(() => Array(str1.length + 1).fill(null));

  for (let i = 0; i <= str1.length; i++) matrix[0][i] = i;
  for (let j = 0; j <= str2.length; j++) matrix[j][0] = j;

  for (let j = 1; j <= str2.length; j++) {
    for (let i = 1; i <= str1.length; i++) {
      const substitutionCost = str1[i - 1] === str2[j - 1] ? 0 : 1;
      matrix[j][i] = Math.min(matrix[j][i - 1] + 1, matrix[j - 1][i] + 1, matrix[j - 1][i - 1] + substitutionCost);
    }
  }
  return matrix[str2.length][str1.length];
}

function findMatches(str1: string, str2: string): string[] {
  const words1 = str1.toLowerCase().split(/\s+/);
  const words2 = str2.toLowerCase().split(/\s+/);
  const matches: string[] = [];

  for (let i = 0; i < words1.length - 2; i++) {
    for (let j = 0; j < words2.length - 2; j++) {
      let matchLength = 0;
      while (
        i + matchLength < words1.length &&
        j + matchLength < words2.length &&
        words1[i + matchLength] === words2[j + matchLength]
      ) {
        matchLength++;
      }
      if (matchLength >= 3) {
        matches.push(words1.slice(i, i + matchLength).join(" "));
      }
    }
  }

  return [...new Set(matches)];
}
