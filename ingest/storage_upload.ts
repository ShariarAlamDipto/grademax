/**
 * storage_upload.ts
 * Upload visual crops and page renders to Supabase Storage
 */
import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = process.env.SUPABASE_URL!
const SUPABASE_SERVICE_ROLE = process.env.SUPABASE_SERVICE_ROLE!

if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE) {
  throw new Error('Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE')
}

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE, {
  auth: { persistSession: false }
})

export interface UploadResult {
  url: string
  path: string
  size: number
}

/**
 * Upload a single page PNG
 */
export async function uploadPagePng(
  paperCode: string,
  pageNumber: number,
  pngBuffer: Buffer
): Promise<UploadResult> {
  const storagePath = `papers/${paperCode}/pages/page_${String(pageNumber).padStart(3, '0')}.png`
  
  const { error } = await supabase.storage
    .from('papers')
    .upload(storagePath, pngBuffer, {
      contentType: 'image/png',
      upsert: true
    })
  
  if (error) {
    throw new Error(`Failed to upload page ${pageNumber}: ${error.message}`)
  }
  
  const { data: { publicUrl } } = supabase.storage
    .from('papers')
    .getPublicUrl(storagePath)
  
  return {
    url: publicUrl,
    path: storagePath,
    size: pngBuffer.length
  }
}

/**
 * Upload a question crop PNG
 * Uses visual_hash as filename for automatic deduplication
 */
export async function uploadCropPng(
  paperCode: string,
  questionNumber: string,
  pngBuffer: Buffer,
  visualHash: string
): Promise<UploadResult> {
  // Use hash for dedup, but keep readable subfolder structure
  const safeQuestionNum = questionNumber.replace(/[()]/g, '_')
  const storagePath = `papers/${paperCode}/crops/${safeQuestionNum}_${visualHash.substring(0, 8)}.png`
  
  const { error } = await supabase.storage
    .from('papers')
    .upload(storagePath, pngBuffer, {
      contentType: 'image/png',
      upsert: true
    })
  
  if (error) {
    throw new Error(`Failed to upload crop ${questionNumber}: ${error.message}`)
  }
  
  const { data: { publicUrl } } = supabase.storage
    .from('papers')
    .getPublicUrl(storagePath)
  
  return {
    url: publicUrl,
    path: storagePath,
    size: pngBuffer.length
  }
}

/**
 * Upload multiple page PNGs in batch
 */
export async function uploadAllPages(
  paperCode: string,
  pagePngs: Buffer[]
): Promise<UploadResult[]> {
  console.log(`  📤 Uploading ${pagePngs.length} page renders...`)
  
  const results: UploadResult[] = []
  
  for (let i = 0; i < pagePngs.length; i++) {
    const result = await uploadPagePng(paperCode, i + 1, pagePngs[i])
    results.push(result)
  }
  
  const totalSize = results.reduce((sum, r) => sum + r.size, 0)
  console.log(`    ✓ Uploaded ${results.length} pages (${(totalSize / 1024 / 1024).toFixed(1)} MB)`)
  
  return results
}

/**
 * Upload multiple crop PNGs in batch
 */
export async function uploadAllCrops(
  paperCode: string,
  crops: Array<{ questionNumber: string; pngBuffer: Buffer; visualHash: string }>
): Promise<UploadResult[]> {
  console.log(`  📤 Uploading ${crops.length} question crops...`)
  
  const results: UploadResult[] = []
  
  for (const crop of crops) {
    const result = await uploadCropPng(
      paperCode,
      crop.questionNumber,
      crop.pngBuffer,
      crop.visualHash
    )
    results.push(result)
  }
  
  const totalSize = results.reduce((sum, r) => sum + r.size, 0)
  console.log(`    ✓ Uploaded ${results.length} crops (${(totalSize / 1024).toFixed(1)} KB)`)
  
  return results
}

/**
 * Insert page records into database
 */
export async function insertPageRecords(
  paperId: string,
  pageUploads: Array<{ pageNumber: number; upload: UploadResult; width: number; height: number; dpi: number }>
): Promise<void> {
  const records = pageUploads.map(p => ({
    paper_id: paperId,
    page_number: p.pageNumber,
    visual_url: p.upload.url,
    width: p.width,
    height: p.height,
    dpi: p.dpi,
    file_size_kb: Math.round(p.upload.size / 1024)
  }))
  
  const { error } = await supabase
    .from('paper_pages')
    .upsert(records, { onConflict: 'paper_id,page_number' })
  
  if (error) {
    throw new Error(`Failed to insert page records: ${error.message}`)
  }
  
  console.log(`    ✓ Inserted ${records.length} page records`)
}

/**
 * Check if crop already exists by visual_hash (deduplication)
 */
export async function checkCropExists(visualHash: string): Promise<{ exists: boolean; questionId?: string }> {
  const { data, error } = await supabase
    .from('questions')
    .select('id')
    .eq('visual_hash', visualHash)
    .limit(1)
    .single()
  
  if (error && error.code !== 'PGRST116') { // PGRST116 = not found
    throw new Error(`Failed to check crop existence: ${error.message}`)
  }
  
  return {
    exists: !!data,
    questionId: data?.id
  }
}
