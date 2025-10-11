/**
 * embeddings.ts
 * Generate embeddings using @xenova/transformers (MiniLM-L6-v2)
 */
import { pipeline, type FeatureExtractionPipeline } from '@xenova/transformers'

let embedder: FeatureExtractionPipeline | null = null

/**
 * Initialize the embedder (lazy load)
 */
async function getEmbedder(): Promise<FeatureExtractionPipeline> {
  if (!embedder) {
    console.log('Loading Xenova/all-MiniLM-L6-v2 model...')
    embedder = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2')
    console.log('Model loaded ✓')
  }
  return embedder
}

/**
 * Generate embedding vector for text
 * Returns 384-dimensional vector
 */
export async function embed(text: string): Promise<number[]> {
  const model = await getEmbedder()
  
  // Truncate long text
  const truncated = text.slice(0, 512)
  
  const output = await model(truncated, { pooling: 'mean', normalize: true })
  
  // Extract the data array
  return Array.from(output.data as Float32Array)
}

/**
 * Calculate cosine similarity between two vectors
 * Returns value between -1 and 1 (1 = identical)
 */
export function cosineSimilarity(a: number[], b: number[]): number {
  if (a.length !== b.length) {
    throw new Error('Vectors must have same length')
  }
  
  let dotProduct = 0
  let normA = 0
  let normB = 0
  
  for (let i = 0; i < a.length; i++) {
    dotProduct += a[i] * b[i]
    normA += a[i] * a[i]
    normB += b[i] * b[i]
  }
  
  normA = Math.sqrt(normA)
  normB = Math.sqrt(normB)
  
  if (normA === 0 || normB === 0) return 0
  
  return dotProduct / (normA * normB)
}
