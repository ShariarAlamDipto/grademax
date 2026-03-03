const https = require('https');

function fetch(url) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, {
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' }
    }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        return fetch(res.headers.location).then(resolve).catch(reject);
      }
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: data }));
    });
    req.on('error', reject);
  });
}

// Fetch the RSC payload directly using Next.js flight endpoint
function fetchRSC(url) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, {
      headers: { 
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'RSC': '1',
        'Next-Router-State-Tree': '%5B%22%22%2C%7B%22children%22%3A%5B%22igcse%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%5D%7D%5D%7D%2Cnull%2Cnull%2Ctrue%5D',
        'Next-Url': '/igcse'
      }
    }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        return fetchRSC(res.headers.location).then(resolve).catch(reject);
      }
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: data }));
    });
    req.on('error', reject);
  });
}

async function main() {
  // 1. Get the IGCSE page and extract ALL RSC payload data
  console.log('=== Extracting RSC Data from IGCSE page ===\n');
  const igcse = await fetch('https://www.paperlords.org/igcse');
  
  // Extract all RSC push payloads
  const rscRegex = /self\.__next_f\.push\(\[1,"([\s\S]*?)"\]\)/g;
  let match;
  let allPayload = '';
  while ((match = rscRegex.exec(igcse.body)) !== null) {
    // Unescape the JSON string
    const payload = match[1].replace(/\\"/g, '"').replace(/\\n/g, '\n').replace(/\\\\/g, '\\');
    allPayload += payload + '\n';
  }
  
  console.log('Total RSC payload length:', allPayload.length);
  
  // Find all URLs/links in the payload
  const urlRegex = /\/igcse\/[a-zA-Z0-9\-_\/]+/g;
  const urls = [...new Set(allPayload.match(urlRegex) || [])];
  console.log('\n--- IGCSE URLs found in payload ---');
  urls.forEach(u => console.log(' ', u));
  
  // Find subject-related text
  const subjectRegex = /(?:physics|chemistry|biology|mathematics|maths|english|economics|business|accounting|computer|history|geography|ict|science|arabic|french|spanish)/gi;
  const subjects = [...new Set((allPayload.match(subjectRegex) || []).map(s => s.toLowerCase()))];
  console.log('\n--- Subjects mentioned ---');
  subjects.forEach(s => console.log(' ', s));
  
  // Find any PDF or download URLs
  const pdfRegex = /https?:\/\/[^\s"']+\.pdf/gi;
  const pdfs = [...new Set(allPayload.match(pdfRegex) || [])];
  console.log('\n--- PDF URLs ---');
  pdfs.forEach(p => console.log(' ', p));
  
  // Find any href patterns
  const hrefPattern = /href[":]+([^"'\s,}]+)/g;
  const hrefs = [];
  let hm;
  while ((hm = hrefPattern.exec(allPayload)) !== null) {
    if (!hm[1].startsWith('/_next') && !hm[1].includes('pagead') && !hm[1].includes('clerk') && !hm[1].includes('favicon') && hm[1].length > 1) {
      hrefs.push(hm[1]);
    }
  }
  console.log('\n--- All relevant hrefs in RSC ---');
  [...new Set(hrefs)].forEach(h => console.log(' ', h));
  
  // Print a chunk of the decoded payload to find patterns
  console.log('\n--- Decoded RSC Payload (key sections, looking for subject cards/links) ---');
  // Find sections containing subject info
  const lines = allPayload.split('\n');
  for (const line of lines) {
    if (line.length > 200 && (line.includes('subject') || line.includes('Subject') || line.includes('paper') || line.includes('Paper') || line.includes('igcse'))) {
      console.log('\nRelevant line (first 2000):', line.substring(0, 2000));
    }
  }
  
  // Try the RSC endpoint directly
  console.log('\n\n=== Trying RSC Flight Endpoint ===');
  try {
    const rsc = await fetchRSC('https://www.paperlords.org/igcse');
    console.log('RSC Status:', rsc.status);
    console.log('RSC ContentType:', rsc.headers['content-type']);
    console.log('RSC Body length:', rsc.body.length);
    console.log('RSC Body (first 5000):', rsc.body.substring(0, 5000));
    
    // Extract data from RSC response
    const rscUrls = [...new Set(rsc.body.match(/\/igcse\/[a-zA-Z0-9\-_\/]+/g) || [])];
    console.log('\nRSC URLs:', rscUrls);
    
    const rscSubjects = [...new Set((rsc.body.match(subjectRegex) || []).map(s => s.toLowerCase()))];
    console.log('RSC Subjects:', rscSubjects);
  } catch(e) {
    console.log('RSC Error:', e.message);
  }
  
  // Try some specific URL patterns
  console.log('\n\n=== Testing More URL Patterns ===');
  const morePaths = [
    '/igcse/physics/2024',
    '/papers/physics',
    '/subject/physics',
    '/edexcel-igcse-physics',
    '/download',
    '/api/papers',
    '/api/subjects',
  ];
  
  for (const p of morePaths) {
    try {
      const res = await fetch('https://www.paperlords.org' + p);
      const titleMatch = res.body.match(/<title>([^<]+)<\/title>/i);
      const status = res.status;
      const hasContent = res.body.length > 7000;
      console.log(`${p} -> ${status} (${res.body.length} bytes) ${titleMatch ? titleMatch[1] : ''}`);
    } catch(e) {
      console.log(`${p} -> ERROR: ${e.message}`);
    }
  }
}

main().catch(console.error);
