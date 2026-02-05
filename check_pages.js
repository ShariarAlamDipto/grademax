const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
  'https://tybaetnvnfgniotdfxze.supabase.co',
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR5YmFldG52bmZnbmlvdGRmeHplIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcwOTkzMTcsImV4cCI6MjA3MjY3NTMxN30.QRxEmsZFtp0LHFycU6pljuFqJineV8AcTpjo4nBAYes'
);

async function checkPages() {
  // Maths B subject ID
  const mathsBSubjectId = 'af08fe67-37e2-4e20-9550-30103c4fe91a';
  
  // Get papers for Maths B
  const { data: papers, error: paperError } = await supabase
    .from('papers')
    .select('id, year, season, paper_number')
    .eq('subject_id', mathsBSubjectId)
    .limit(5);
  
  if (paperError) {
    console.log('Paper error:', paperError);
    return;
  }
  
  console.log('Maths B Papers:', papers);
  
  if (!papers || papers.length === 0) {
    console.log('No papers found for Maths B!');
    return;
  }
  
  // Get pages for these papers
  const paperIds = papers.map(p => p.id);
  const { data: pages, error: pageError } = await supabase
    .from('pages')
    .select('id, question_number, topics, is_question, qp_page_url, difficulty')
    .in('paper_id', paperIds)
    .limit(20);
  
  if (pageError) {
    console.log('Page error:', pageError);
    return;
  }
  
  console.log('\nMaths B Pages:');
  if (pages && pages.length > 0) {
    pages.forEach(p => {
      console.log(`  Q${p.question_number}: topics=${JSON.stringify(p.topics)}, is_question=${p.is_question}, has_url=${!!p.qp_page_url}`);
    });
  } else {
    console.log('No pages found!');
  }
  
  // Check how many pages have topics
  const { data: topicStats, error: statsError } = await supabase
    .from('pages')
    .select('topics')
    .in('paper_id', paperIds);
  
  if (topicStats) {
    const withTopics = topicStats.filter(p => p.topics && p.topics.length > 0);
    console.log(`\nTopic Stats: ${withTopics.length}/${topicStats.length} pages have topics`);
  }
}

checkPages().catch(console.error);
