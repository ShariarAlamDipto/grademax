import { NextResponse } from "next/server"
import { createClient } from "@supabase/supabase-js"

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

export async function GET(req: Request) {
  try {
    // Check environment variables
    if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
      console.error('Topics API: Missing Supabase credentials');
      return NextResponse.json([], { status: 200 });
    }

    const url = new URL(req.url)
    const subjectId = url.searchParams.get('subjectId')
    
    if (!subjectId) {
      console.warn('Topics API: No subjectId provided')
      return NextResponse.json([], { status: 200 })
    }
    
    const { data, error } = await supabase
      .from('topics')
      .select('id, name, code, description')
      .eq('subject_id', subjectId)
      .order('code')
    
    if (error) {
      console.error('Topics API error:', error.message, error.details, error.hint)
      return NextResponse.json([], { status: 200 })
    }
    
    console.log(`Topics API: Returning ${data?.length || 0} topics for subject ${subjectId}`);
    return NextResponse.json(data || [], { status: 200 })
  } catch (err) {
    console.error('Topics API exception:', err)
    return NextResponse.json([], { status: 200 })
  }
}
