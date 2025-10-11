/**
 * check_db.ts
 * Quick script to check what's in the database
 */
import 'dotenv/config'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE!
)

async function main() {
  console.log('📊 Database Status Check\n')
  
  // Count subjects
  const { count: subjectCount } = await supabase
    .from('subjects')
    .select('*', { count: 'exact', head: true })
  console.log(`Subjects: ${subjectCount}`)
  
  // Count topics
  const { count: topicCount } = await supabase
    .from('topics')
    .select('*', { count: 'exact', head: true })
  console.log(`Topics: ${topicCount}`)
  
  // Count papers
  const { count: paperCount } = await supabase
    .from('papers')
    .select('*', { count: 'exact', head: true })
  console.log(`Papers: ${paperCount}`)
  
  // Count questions
  const { count: questionCount } = await supabase
    .from('questions')
    .select('*', { count: 'exact', head: true })
  console.log(`Questions: ${questionCount}`)
  
  // Sample questions
  const { data: sampleQuestions } = await supabase
    .from('questions')
    .select('id, question_number, marks, difficulty, text')
    .limit(10)
  
  console.log('\n📝 Sample Questions:')
  sampleQuestions?.forEach(q => {
    console.log(`  ${q.question_number} [${q.marks || '?'} marks, diff: ${q.difficulty}]`)
    console.log(`    ${q.text.substring(0, 80)}...`)
  })
  
  // Count questions with topics
  const { count: taggedCount } = await supabase
    .from('question_topics')
    .select('*', { count: 'exact', head: true })
  console.log(`\n🏷️  Question-Topic links: ${taggedCount}`)
  
  // Count markschemes
  const { count: msCount } = await supabase
    .from('markschemes')
    .select('*', { count: 'exact', head: true })
  console.log(`📋 Markschemes: ${msCount}`)
}

main().catch(console.error)
