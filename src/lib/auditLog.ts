/**
 * Admin audit trail logger.
 * All writes are fire-and-forget — never throws.
 *
 * Required DB table (run once in Supabase SQL editor):
 *
 *   CREATE TABLE IF NOT EXISTS admin_audit_log (
 *     id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 *     created_at  timestamptz DEFAULT now(),
 *     admin_email text,
 *     action      text NOT NULL,   -- e.g. "upload_paper", "delete_paper", "update_role"
 *     entity_type text,            -- e.g. "paper", "subject", "user"
 *     entity_id   text,            -- uuid or composite key
 *     details     jsonb            -- arbitrary context
 *   );
 *
 *   CREATE INDEX IF NOT EXISTS admin_audit_log_created_at ON admin_audit_log (created_at DESC);
 */

import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export interface AuditEntry {
  admin_email?: string | null
  action: string
  entity_type?: string
  entity_id?: string
  details?: Record<string, unknown>
}

export async function logAdminAction(entry: AuditEntry): Promise<void> {
  try {
    const db = getSupabaseAdmin()
    if (!db) return
    await db.from("admin_audit_log").insert({
      admin_email: entry.admin_email || null,
      action: entry.action,
      entity_type: entry.entity_type || null,
      entity_id: entry.entity_id || null,
      details: entry.details || null,
    })
  } catch {
    // Non-fatal — silently swallow so audit failures never break user-facing flows
  }
}
