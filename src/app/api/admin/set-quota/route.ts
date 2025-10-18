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
    const { userId, maxPerDay } = body;
    
    if (!userId) {
      return NextResponse.json(
        { error: 'User ID is required' },
        { status: 400 }
      );
    }
    
    // Update quota
    const { data, error } = await supabase
      .from('user_permissions')
      .update({
        max_worksheets_per_day: maxPerDay,
        notes: `Quota set to ${maxPerDay > 0 ? maxPerDay + ' per day' : 'unlimited'} on ${new Date().toLocaleDateString()}`,
      })
      .eq('user_id', userId)
      .select();
    
    if (error) {
      throw error;
    }
    
    // Log audit event (Phase 1)
    const ipAddress = request.headers.get('x-forwarded-for') || request.headers.get('x-real-ip') || 'unknown';
    await getAuditLogger().log({
      eventType: 'permission.quota_updated',
      eventCategory: 'permission',
      actorUserId: authResult.user!.id,
      actorEmail: authResult.user!.email!,
      targetUserId: userId,
      targetResourceType: 'user_permission',
      details: { 
        maxPerDay,
        maxPerMonth: maxPerDay ? maxPerDay * 30 : null
      },
      ipAddress: ipAddress,
      status: 'success'
    });
    
    return NextResponse.json({ 
      success: true,
      data 
    });
  } catch (error) {
    console.error('Error setting quota:', error);
    return NextResponse.json(
      { error: 'Failed to set quota' },
      { status: 500 }
    );
  }
}
