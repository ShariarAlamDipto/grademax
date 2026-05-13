/**
 * Server-side Appwrite client for the lectures bucket.
 *
 * Use this from Next.js API routes / server actions only. The API key is
 * privileged (buckets/files read+write) and must never reach the browser.
 *
 * For browser-side rendering of public file URLs, construct them directly:
 *   `${NEXT_PUBLIC_APPWRITE_ENDPOINT}/storage/buckets/${BUCKET}/files/${id}/view?project=${PROJECT}`
 */
import { Client, Storage } from "node-appwrite";

const ENDPOINT   = process.env.APPWRITE_ENDPOINT
export const APPWRITE_PROJECT_ID = process.env.APPWRITE_PROJECT_ID || "";
export const APPWRITE_BUCKET_ID  = process.env.APPWRITE_BUCKET_ID || "grademax-lectures";
const API_KEY    = process.env.APPWRITE_API_KEY;

let _storage: Storage | null = null;

export function getAppwriteStorage(): Storage {
  if (_storage) return _storage;
  if (!ENDPOINT)   throw new Error("APPWRITE_ENDPOINT not configured");
  if (!APPWRITE_PROJECT_ID) throw new Error("APPWRITE_PROJECT_ID not configured");
  if (!API_KEY)    throw new Error("APPWRITE_API_KEY not configured");

  const client = new Client()
    .setEndpoint(ENDPOINT)
    .setProject(APPWRITE_PROJECT_ID)
    .setKey(API_KEY);

  _storage = new Storage(client);
  return _storage;
}

/**
 * Build the public download URL for a file in the lectures bucket.
 * `view` returns the raw file (browser previews PDFs/MP4s inline);
 * `download` adds a Content-Disposition: attachment header.
 */
export function buildAppwriteFileUrl(
  fileId: string,
  mode: "view" | "download" = "view",
): string {
  const endpoint = process.env.NEXT_PUBLIC_APPWRITE_ENDPOINT
    || ENDPOINT
    || "https://sgp.cloud.appwrite.io/v1";
  const project = process.env.NEXT_PUBLIC_APPWRITE_PROJECT_ID || APPWRITE_PROJECT_ID;
  const bucket  = process.env.NEXT_PUBLIC_APPWRITE_BUCKET_ID  || APPWRITE_BUCKET_ID;
  return `${endpoint}/storage/buckets/${bucket}/files/${fileId}/${mode}?project=${project}`;
}
