import { NextResponse } from "next/server"
import { createClient } from "@supabase/supabase-js"

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

export async function GET(req: Request) {
  const url = new URL(req.url)
  const subjectId = url.searchParams.get('subjectId')
  
  if (!subjectId) return NextResponse.json({ error: 'subjectId required' }, { status: 400 })
  
  const { data, error } = await supabase
    .from('topics')
    .select('id, name, code, spec_ref')
    .eq('subject_id', subjectId)
    .order('code')
  
  if (error) return NextResponse.json({ error: error.message }, { status: 400 })
  return NextResponse.json(data || [])
}
