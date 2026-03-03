const https = require('https');

function fetch(url, headers = {}) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, {
      headers: { 
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ...headers
      }
    }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        const loc = res.headers.location.startsWith('http') ? res.headers.location : `https://www.paperlords.org${res.headers.location}`;
        return fetch(loc, headers).then(resolve).catch(reject);
      }
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: data }));
    });
    req.on('error', reject);
  });
}

async function main() {
  // Get the full RSC payload and dump everything
  console.log('=== Full RSC Payload ===\n');
  const rsc = await fetch('https://www.paperlords.org/igcse', { 'RSC': '1' });
  
  // Dump the entire RSC payload
  console.log(rsc.body);
  
  console.log('\n\n=== Looking for Subject Card data ===\n');
  
  // Search for patterns like href with subject codes or names
  const hrefMatches = rsc.body.match(/href["\s:]*"?\/[^"\s,}\]]+/g);
  console.log('href patterns:', hrefMatches);
  
  // Look for subject code patterns (4PH1, 0580, etc)
  const codePattern = /[0-9]{4}[A-Z]?[0-9]?/g;
  const codes = [...new Set(rsc.body.match(codePattern) || [])];
  console.log('\nSubject codes:', codes);
  
  // Now try to find the JS chunk that contains the subject list
  console.log('\n\n=== Checking JS Chunks for API endpoints ===\n');
  const jsChunks = ['56b1768815112403', '450b8ed6670677a4'];
  for (const chunk of jsChunks) {
    try {
      const js = await fetch(`https://www.paperlords.org/_next/static/chunks/${chunk}.js`);
      if (js.status === 200) {
        console.log(`\nChunk ${chunk}: ${js.body.length} bytes`);
        // Look for API endpoints, fetch calls, supabase references
        const apiPatterns = js.body.match(/(?:api|supabase|fetch|papers|subjects|download|pdf|\.pdf|igcse|physics)[^;]{0,200}/gi);
        if (apiPatterns) {
          console.log('API patterns found:');
          [...new Set(apiPatterns)].forEach(p => console.log('  ', p.substring(0, 200)));
        }
      }
    } catch(e) {
      console.log(`Chunk ${chunk}: ${e.message}`);
    }
  }
  
  // Try to check if there's a Supabase or external API
  console.log('\n\n=== Checking for Supabase/Backend URLs ===');
  const homepage = await fetch('https://www.paperlords.org/');
  const supabaseUrls = homepage.body.match(/https:\/\/[a-z0-9]+\.supabase\.co[^"'\s]*/g);
  console.log('Supabase URLs:', supabaseUrls);
  
  const apiUrls = homepage.body.match(/(?:api|backend|server)[a-zA-Z0-9\.\-]*\.(com|org|io|dev|app)[^"'\s]*/gi);
  console.log('API domains:', apiUrls);
}

main().catch(console.error);
