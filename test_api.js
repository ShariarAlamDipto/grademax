const https = require('https');
const http = require('http');

const data = JSON.stringify({
  subjectCode: "af08fe67-37e2-4e20-9550-30103c4fe91a",
  topics: ["1"],  // Topic "Number"
  limit: 5
});

const options = {
  hostname: 'localhost',
  port: 3000,
  path: '/api/worksheets/generate-v2',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Content-Length': data.length
  }
};

const req = http.request(options, (res) => {
  let body = '';
  res.on('data', (chunk) => {
    body += chunk;
  });
  res.on('end', () => {
    const result = JSON.parse(body);
    console.log('Status:', res.statusCode);
    console.log('Pages returned:', result.pages?.length || 0);
    if (result.pages && result.pages.length > 0) {
      console.log('\nSample questions:');
      result.pages.slice(0, 3).forEach(p => {
        console.log(`  Q${p.question_number}: Year ${p.papers?.year}, Topics: ${p.topics?.join(', ')}`);
        console.log(`    URL: ${p.qp_page_url?.substring(0, 80)}...`);
      });
    } else {
      console.log('Result:', JSON.stringify(result, null, 2));
    }
  });
});

req.on('error', (e) => {
  console.error('Error:', e.message);
});

req.write(data);
req.end();
