// Test if questions exist in database
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = 'https://tybaetnvnfgniotdfxze.supabase.co';
const supabaseAnonKey = 'REDACTED';

const supabase = createClient(supabaseUrl, supabaseAnonKey);

async function testQuestionsCount() {
  console.log('🔍 Checking Questions in Database...\n');

  // Get Physics subject
  const { data: physics } = await supabase
    .from('subjects')
    .select('id, code, name')
    .eq('code', '4PH1')
    .single();

  if (!physics) {
    console.log('❌ Physics subject not found');
    return;
  }

  console.log(`✅ Found subject: ${physics.name} (${physics.code})`);
  console.log(`   Subject ID: ${physics.id}\n`);

  // Count papers
  const { data: papers, error: papersError } = await supabase
    .from('papers')
    .select('id, year, season, paper_number')
    .eq('subject_code', '4PH1');

  if (papersError) {
    console.log('❌ Error checking papers:', papersError.message);
  } else {
    console.log(`📄 Papers: ${papers?.length || 0}`);
    if (papers && papers.length > 0) {
      papers.forEach(p => {
        console.log(`   - ${p.year} ${p.season} Paper ${p.paper_number}`);
      });
    }
  }

  // Count questions
  const { count: questionCount, error: questionsError } = await supabase
    .from('questions')
    .select('*', { count: 'exact', head: true })
    .in('paper_id', papers?.map(p => p.id) || []);

  if (questionsError) {
    console.log('❌ Error checking questions:', questionsError.message);
  } else {
    console.log(`\n❓ Questions: ${questionCount || 0}`);
  }

  // Check question_topics
  const { count: topicTagCount } = await supabase
    .from('question_topics')
    .select('*', { count: 'exact', head: true });

  console.log(`🏷️  Topic Tags: ${topicTagCount || 0}`);

  console.log('\n' + '='.repeat(60));
  
  if ((questionCount || 0) === 0) {
    console.log('⚠️  NO QUESTIONS FOUND!');
    console.log('');
    console.log('This is why worksheet generation fails.');
    console.log('');
    console.log('👉 Next Steps:');
    console.log('   1. Get some past paper PDFs (QP + MS)');
    console.log('   2. Run the ingestion pipeline');
    console.log('   3. Questions will be extracted and added');
    console.log('');
    console.log('📖 See: INGESTION_GUIDE.md for instructions');
  } else {
    console.log('✅ Questions exist! Worksheet generation should work.');
    console.log('');
    console.log('Go to: http://localhost:3001/worksheets');
    console.log('Select Physics → Choose topics → Generate!');
  }
  
  console.log('='.repeat(60));
}

testQuestionsCount().catch(console.error);
