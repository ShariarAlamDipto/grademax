import { createClient } from '@supabase/supabase-js';
import { NextResponse } from 'next/server';
import { checkAdminAuth } from '@/lib/adminAuth';
import { getAuditLogger } from '@/lib/auditLogger';

export async function POST(request: Request) {
  try {
    // Check admin authentication
    const authResult = await checkAdminAuth();
    
    if (!authResult.isAdmin) {
      return NextResponse.json(
        { error: authResult.error || 'Unauthorized' },
        { status: 403 }
      );
    }
    
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
    const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
    
    const supabase = createClient(supabaseUrl, supabaseKey);
    
    const body = await request.json();
    const { userId } = body;
    
    if (!userId) {
      return NextResponse.json(
        { error: 'User ID is required' },
        { status: 400 }
      );
    }
    
    // Get target user details
    const { data: targetUser } = await supabase.auth.admin.getUserById(userId);
    
    // Update permission
    const { data, error } = await supabase
      .from('user_permissions')
      .update({
        can_generate_worksheets: false,
        is_active: false,
        notes: `Permission revoked on ${new Date().toLocaleDateString()}`,
      })
      .eq('user_id', userId)
      .select();
    
    if (error) {
      throw error;
    }
    
    // Log audit event (Phase 1)
    const ipAddress = request.headers.get('x-forwarded-for') || request.headers.get('x-real-ip') || 'unknown';
    await getAuditLogger().logPermissionRevoked(
      authResult.user!.id,
      authResult.user!.email!,
      userId,
      targetUser?.user?.email || 'unknown',
      ipAddress
    );
    
    return NextResponse.json({ 
      success: true,
      data 
    });
  } catch (error) {
    console.error('Error revoking permission:', error);
    return NextResponse.json(
      { error: 'Failed to revoke permission' },
      { status: 500 }
    );
  }
}
