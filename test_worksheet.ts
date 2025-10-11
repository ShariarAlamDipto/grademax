/**
 * test_worksheet.ts
 * Test worksheet generation API
 */

async function testWorksheetGeneration() {
  const url = 'http://127.0.0.1:3000/api/worksheets/generate'
  const body = {
    subjectId: '7c4e1f89-e80d-43bf-8c3e-26f0a5e4e24e',
    topicIds: ['58e86da0-7ff7-4b72-9d54-5c8c47fe9d07'], // 6a - Magnetism
    count: 5
  }
  
  console.log('Testing:', url)
  console.log('Body:', JSON.stringify(body, null, 2))
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    })
    
    const data = await response.json()
    
    console.log('\nStatus:', response.status)
    console.log('Response:', JSON.stringify(data, null, 2))
    
    if (data.items) {
      console.log(`\n✅ Generated ${data.items.length} questions`)
      data.items.forEach((item: { question: { questionNumber: string, text: string }, markscheme?: { text: string } }) => {
        console.log(`\n  ${item.question.questionNumber}: ${item.question.text.substring(0, 60)}...`)
        if (item.markscheme) {
          console.log(`    Markscheme: ${item.markscheme.text.substring(0, 60)}...`)
        }
      })
    }
  } catch (error) {
    console.error('❌ Error:', error)
    console.log('\nTrying to check if server is running...')
    try {
      const healthCheck = await fetch('http://127.0.0.1:3000/')
      console.log('Server responded:', healthCheck.status)
    } catch {
      console.error('Server not reachable')
    }
  }
}

testWorksheetGeneration().catch(console.error)
