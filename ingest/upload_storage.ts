/**
 * upload_storage.ts
 * Upload PDFs to Supabase Storage
 */
import { createClient } from '@supabase/supabase-js'
import fs from 'fs'
import path from 'path'

/**
 * Upload PDF to Supabase Storage
 * Creates 'papers' bucket if it doesn't exist
 * Returns public URL
 */
export async function uploadPdf(
  supabaseUrl: string,
  supabaseKey: string,
  localPath: string,
  destKey: string
): Promise<{ publicUrl: string }> {
  const supabase = createClient(supabaseUrl, supabaseKey)
  
  // Ensure bucket exists
  const { data: buckets } = await supabase.storage.listBuckets()
  const hasPapersBucket = buckets?.some(b => b.name === 'papers')
  
  if (!hasPapersBucket) {
    console.log('Creating papers bucket...')
    await supabase.storage.createBucket('papers', {
      public: true,
      fileSizeLimit: 52428800 // 50MB
    })
  }
  
  // Read file
  const fileBuffer = fs.readFileSync(localPath)
  const ext = path.extname(localPath)
  const contentType = ext === '.pdf' ? 'application/pdf' : 'application/octet-stream'
  
  // Upload
  const { error: uploadError } = await supabase.storage
    .from('papers')
    .upload(destKey, fileBuffer, {
      contentType,
      upsert: true
    })
  
  if (uploadError) {
    throw new Error(`Upload failed: ${uploadError.message}`)
  }
  
  // Get public URL
  const { data } = supabase.storage
    .from('papers')
    .getPublicUrl(destKey)
  
  return { publicUrl: data.publicUrl }
}
