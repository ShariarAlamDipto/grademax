const https = require('https');
const http = require('http');

function fetch(url) {
  const client = url.startsWith('https') ? https : http;
  return new Promise((resolve, reject) => {
    const req = client.get(url, {
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

async function main() {
  // 1. Check the IGCSE page for subject links
  console.log('=== IGCSE Page Deep Analysis ===\n');
  const igcse = await fetch('https://www.paperlords.org/igcse');
  
  // Extract all links
  const hrefRegex = /href="([^"]+)"/g;
  const allLinks = [];
  let m;
  while ((m = hrefRegex.exec(igcse.body)) !== null) {
    allLinks.push(m[1]);
  }
  console.log('All links:', allLinks.filter(l => !l.startsWith('/_next') && !l.startsWith('https://pagead') && !l.startsWith('https://clerk') && l !== '/favicon.ico?favicon.1ab3ad72.ico'));
  
  // Extract __NEXT_DATA__ for subject data
  const nextDataMatch = igcse.body.match(/<script id="__NEXT_DATA__"[^>]*>(.*?)<\/script>/);
  if (nextDataMatch) {
    const nextData = JSON.parse(nextDataMatch[1]);
    console.log('\n__NEXT_DATA__ keys:', Object.keys(nextData));
    console.log('Page props keys:', Object.keys(nextData.props?.pageProps || {}));
    console.log('Page data (first 3000):', JSON.stringify(nextData.props?.pageProps, null, 2).substring(0, 3000));
  } else {
    console.log('No __NEXT_DATA__ found (might be App Router with RSC)');
  }
  
  // Look for RSC payload or inline data
  const scriptDataRegex = /<script[^>]*>([\s\S]*?)<\/script>/g;
  let scriptMatch;
  const interestingScripts = [];
  while ((scriptMatch = scriptDataRegex.exec(igcse.body)) !== null) {
    const content = scriptMatch[1];
    if (content.length > 100 && (content.includes('subject') || content.includes('paper') || content.includes('igcse') || content.includes('physics') || content.includes('maths'))) {
      interestingScripts.push(content.substring(0, 500));
    }
  }
  console.log('\nInteresting scripts with subject/paper data:', interestingScripts.length);
  interestingScripts.forEach((s, i) => console.log(`Script ${i}:`, s));
  
  // Check for RSC payload in the HTML body (React Server Components)
  const rsPayloadRegex = /self\.__next_f\.push\(\[.*?\]\)/g;
  let rsMatch;
  const rscPayloads = [];
  while ((rsMatch = rsPayloadRegex.exec(igcse.body)) !== null) {
    rscPayloads.push(rsMatch[0]);
  }
  console.log('\nRSC payloads found:', rscPayloads.length);
  
  // Try to find subject names in the raw HTML
  const subjectPattern = /(?:physics|chemistry|biology|mathematics|maths|english|economics|business|accounting|computer|history|geography|ict)/gi;
  const subjectMatches = igcse.body.match(subjectPattern);
  console.log('\nSubject mentions in HTML:', [...new Set(subjectMatches?.map(s => s.toLowerCase()) || [])]);
  
  // Extract visible text content between tags
  const textContent = igcse.body.replace(/<script[^>]*>[\s\S]*?<\/script>/g, '')
    .replace(/<style[^>]*>[\s\S]*?<\/style>/g, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  console.log('\nVisible text (first 2000):', textContent.substring(0, 2000));
  
  // 2. Try to access a specific subject page
  console.log('\n\n=== Trying Subject Pages ===\n');
  const testPaths = [
    '/igcse/physics',
    '/igcse/4PH1',
    '/igcse/mathematics',
    '/igcse/0580',
    '/papers/igcse/physics',
    '/igcse/edexcel/physics',
    '/igcse/cambridge/physics',
  ];
  
  for (const p of testPaths) {
    try {
      const res = await fetch('https://www.paperlords.org' + p);
      const titleMatch = res.body.match(/<title>([^<]+)<\/title>/i);
      console.log(`${p} -> ${res.status} ${titleMatch ? titleMatch[1] : '(no title)'}`);
      if (res.status === 200 && res.body.length > 7000) {
        // Extract text content
        const text = res.body.replace(/<script[^>]*>[\s\S]*?<\/script>/g, '')
          .replace(/<style[^>]*>[\s\S]*?<\/style>/g, '')
          .replace(/<[^>]+>/g, ' ')
          .replace(/\s+/g, ' ')
          .trim();
        console.log('  Text (first 500):', text.substring(0, 500));
        
        // Find links on this page
        const pageLinks = [];
        let pm;
        const pReg = /href="([^"]+)"/g;
        while ((pm = pReg.exec(res.body)) !== null) {
          if (!pm[1].startsWith('/_next') && !pm[1].includes('pagead') && !pm[1].includes('clerk') && !pm[1].includes('favicon')) {
            pageLinks.push(pm[1]);
          }
        }
        if (pageLinks.length > 0) {
          console.log('  Page links:', pageLinks.slice(0, 15));
        }
      }
    } catch(e) {
      console.log(`${p} -> ERROR: ${e.message}`);
    }
  }
}

main().catch(console.error);
