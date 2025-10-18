import { createClient } from '@supabase/supabase-js';

interface AuditLogEntry {
  eventType: string;
  eventCategory: 'auth' | 'permission' | 'worksheet' | 'admin' | 'security';
  actorUserId?: string;
  actorEmail?: string;
  actorRole?: string;
  targetUserId?: string;
  targetResourceType?: string;
  targetResourceId?: string;
  ipAddress?: string;
  userAgent?: string;
  sessionId?: string;
  details?: Record<string, unknown>;
  status?: 'success' | 'failure' | 'error';
  errorMessage?: string;
}

export class AuditLogger {
  private supabase;

  constructor() {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
    const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
    this.supabase = createClient(supabaseUrl, supabaseKey);
  }

  async log(entry: AuditLogEntry): Promise<string | null> {
    try {
      const { data, error } = await this.supabase.rpc('create_audit_log_entry', {
        p_event_type: entry.eventType,
        p_event_category: entry.eventCategory,
        p_actor_user_id: entry.actorUserId || null,
        p_actor_email: entry.actorEmail || null,
        p_target_user_id: entry.targetUserId || null,
        p_target_resource_type: entry.targetResourceType || null,
        p_target_resource_id: entry.targetResourceId || null,
        p_ip_address: entry.ipAddress || null,
        p_details: entry.details || null,
        p_status: entry.status || 'success',
      });

      if (error) {
        console.error('Failed to create audit log:', error);
        return null;
      }

      return data;
    } catch (error) {
      console.error('Audit logging error:', error);
      return null;
    }
  }

  // Convenience methods for common events
  async logLogin(userId: string, email: string, ipAddress?: string, success: boolean = true) {
    return this.log({
      eventType: 'auth.login',
      eventCategory: 'auth',
      actorUserId: userId,
      actorEmail: email,
      ipAddress,
      status: success ? 'success' : 'failure',
    });
  }

  async logLogout(userId: string, email: string, ipAddress?: string) {
    return this.log({
      eventType: 'auth.logout',
      eventCategory: 'auth',
      actorUserId: userId,
      actorEmail: email,
      ipAddress,
      status: 'success',
    });
  }

  async logPermissionGranted(
    adminUserId: string,
    adminEmail: string,
    targetUserId: string,
    targetEmail: string,
    ipAddress?: string
  ) {
    return this.log({
      eventType: 'permission.granted',
      eventCategory: 'permission',
      actorUserId: adminUserId,
      actorEmail: adminEmail,
      targetUserId,
      details: { targetEmail, action: 'grant_worksheet_permission' },
      ipAddress,
      status: 'success',
    });
  }

  async logPermissionRevoked(
    adminUserId: string,
    adminEmail: string,
    targetUserId: string,
    targetEmail: string,
    ipAddress?: string
  ) {
    return this.log({
      eventType: 'permission.revoked',
      eventCategory: 'permission',
      actorUserId: adminUserId,
      actorEmail: adminEmail,
      targetUserId,
      details: { targetEmail, action: 'revoke_worksheet_permission' },
      ipAddress,
      status: 'success',
    });
  }

  async logWorksheetGenerated(
    userId: string,
    email: string,
    worksheetId: string,
    details: {
      subjectCode: string;
      topics: string[];
      questionsCount: number;
      pagesCount: number;
    },
    ipAddress?: string
  ) {
    return this.log({
      eventType: 'worksheet.generated',
      eventCategory: 'worksheet',
      actorUserId: userId,
      actorEmail: email,
      targetResourceType: 'worksheet',
      targetResourceId: worksheetId,
      details,
      ipAddress,
      status: 'success',
    });
  }

  async logQuotaExceeded(
    userId: string,
    email: string,
    quotaType: string,
    currentUsage: number,
    limit: number,
    ipAddress?: string
  ) {
    return this.log({
      eventType: 'quota.exceeded',
      eventCategory: 'security',
      actorUserId: userId,
      actorEmail: email,
      details: { quotaType, currentUsage, limit },
      ipAddress,
      status: 'failure',
      errorMessage: `${quotaType} quota exceeded: ${currentUsage}/${limit}`,
    });
  }

  async logAdminAccess(
    userId: string,
    email: string,
    action: string,
    ipAddress?: string,
    success: boolean = true
  ) {
    return this.log({
      eventType: `admin.${action}`,
      eventCategory: 'admin',
      actorUserId: userId,
      actorEmail: email,
      ipAddress,
      status: success ? 'success' : 'failure',
    });
  }

  async logSecurityEvent(
    eventType: string,
    userId?: string,
    email?: string,
    details?: Record<string, unknown>,
    ipAddress?: string
  ) {
    return this.log({
      eventType: `security.${eventType}`,
      eventCategory: 'security',
      actorUserId: userId,
      actorEmail: email,
      details,
      ipAddress,
      status: 'success',
    });
  }

  // Get recent audit logs (for admin viewing)
  async getRecentLogs(limit: number = 50, category?: string) {
    let query = this.supabase
      .from('audit_log')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(limit);

    if (category) {
      query = query.eq('event_category', category);
    }

    const { data, error } = await query;

    if (error) {
      console.error('Failed to fetch audit logs:', error);
      return [];
    }

    return data || [];
  }

  // Get logs for specific user
  async getUserLogs(userId: string, limit: number = 50) {
    const { data, error } = await this.supabase
      .from('audit_log')
      .select('*')
      .or(`actor_user_id.eq.${userId},target_user_id.eq.${userId}`)
      .order('created_at', { ascending: false })
      .limit(limit);

    if (error) {
      console.error('Failed to fetch user audit logs:', error);
      return [];
    }

    return data || [];
  }

  // Verify hash chain integrity
  async verifyHashChain(limit: number = 1000): Promise<{ valid: boolean; brokenAt?: string }> {
    const { data, error } = await this.supabase
      .from('audit_log')
      .select('id, previous_hash, current_hash, created_at')
      .order('created_at', { ascending: true })
      .limit(limit);

    if (error || !data) {
      return { valid: false };
    }

    for (let i = 1; i < data.length; i++) {
      const current = data[i];
      const previous = data[i - 1];

      if (current.previous_hash !== previous.current_hash) {
        return {
          valid: false,
          brokenAt: current.created_at,
        };
      }
    }

    return { valid: true };
  }
}

// Singleton instance
let auditLogger: AuditLogger | null = null;

export function getAuditLogger(): AuditLogger {
  if (!auditLogger) {
    auditLogger = new AuditLogger();
  }
  return auditLogger;
}
