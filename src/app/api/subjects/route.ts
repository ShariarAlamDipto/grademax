import { NextResponse } from "next/server"
import { createClient } from "@supabase/supabase-js"

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

export async function GET() {
  try {
    // Check environment variables
    if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
      console.error('Subjects API: Missing Supabase credentials');
      console.error('URL exists:', !!process.env.NEXT_PUBLIC_SUPABASE_URL);
      console.error('Key exists:', !!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY);
      return NextResponse.json([], { status: 200 });
    }

    const { data, error } = await supabase
      .from('subjects')
      .select('id, name, code, level, board')
      .order('name')
    
    if (error) {
      console.error('Subjects API error:', error.message, error.details, error.hint);
      return NextResponse.json([], { status: 200 })
    }
    
    console.log(`Subjects API: Returning ${data?.length || 0} subjects`);
    return NextResponse.json(data || [], { status: 200 })
  } catch (err) {
    console.error('Subjects API exception:', err);
    return NextResponse.json([], { status: 200 })
  }
}
