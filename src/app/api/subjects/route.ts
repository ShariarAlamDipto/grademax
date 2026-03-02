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
      return NextResponse.json([], { status: 200 });
    }

    const { data, error } = await supabase
      .from('subjects')
      .select('id, name, code, level, board')
      .order('name')
    
    if (error) {
      return NextResponse.json([], { status: 200 })
    }
    
    return NextResponse.json(data || [], {
      status: 200,
      headers: { 'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=86400' },
    })
  } catch {
    return NextResponse.json([], { status: 200 })
  }
}
