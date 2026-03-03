const https = require('https');

function fetch(url) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, {
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' }
    }, (res) => {
      // Follow redirects
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        console.log(`Redirect ${res.statusCode} -> ${res.headers.location}`);
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
  console.log('=== Checking paperlords.com ===\n');
  
  try {
    const res = await fetch('https://paperlords.org');
    console.log('Status:', res.status);
    console.log('Content-Type:', res.headers['content-type']);
    console.log('Server:', res.headers['server']);
    console.log('Body length:', res.body.length);
    console.log('\nFirst 3000 chars:\n', res.body.substring(0, 3000));
    
    // Detection
    const body = res.body;
    console.log('\n--- Technology Detection ---');
    console.log('Cloudflare:', body.includes('cloudflare') || body.includes('cf-chl'));
    console.log('Next.js:', body.includes('__NEXT_DATA__') || body.includes('_next'));
    console.log('Nuxt/Vue:', body.includes('__NUXT__'));
    console.log('WordPress:', body.includes('wp-content'));
    console.log('Has robots meta:', body.includes('robots'));
    
    // Extract all href links
    const hrefRegex = /href="([^"]+)"/g;
    const links = [];
    let match;
    while ((match = hrefRegex.exec(body)) !== null) {
      if (!match[1].startsWith('#') && !match[1].startsWith('javascript')) {
        links.push(match[1]);
      }
    }
    console.log('\n--- Links found (' + links.length + ') ---');
    links.forEach(l => console.log(' ', l));
    
    // Look for subject/paper patterns
    const subjectLinks = links.filter(l => 
      l.includes('igcse') || l.includes('level') || l.includes('paper') || 
      l.includes('subject') || l.includes('physics') || l.includes('math') ||
      l.includes('download') || l.includes('pdf')
    );
    console.log('\n--- Subject/Paper Links ---');
    subjectLinks.forEach(l => console.log(' ', l));
    
  } catch(e) {
    console.error('Error:', e.message);
  }
  
  // Try common sub-paths
  const paths = ['/igcse', '/a-level', '/sitemap.xml', '/robots.txt'];
  for (const p of paths) {
    try {
      console.log(`\n=== Checking paperlords.com${p} ===`);
      const res = await fetch('https://paperlords.org' + p);
      console.log('Status:', res.status);
      console.log('Body length:', res.body.length);
      if (p === '/robots.txt' || p === '/sitemap.xml') {
        console.log('Content:', res.body.substring(0, 2000));
      } else {
        // Just show title and key links
        const titleMatch = res.body.match(/<title>([^<]+)<\/title>/i);
        if (titleMatch) console.log('Title:', titleMatch[1]);
        
        const hrefRegex2 = /href="([^"]+)"/g;
        const subLinks = [];
        let m;
        while ((m = hrefRegex2.exec(res.body)) !== null) {
          if (m[1].includes('paper') || m[1].includes('subject') || m[1].includes('pdf') || m[1].includes('download')) {
            subLinks.push(m[1]);
          }
        }
        if (subLinks.length > 0) {
          console.log('Paper-related links:', subLinks.slice(0, 20));
        }
        console.log('First 1500 chars:', res.body.substring(0, 1500));
      }
    } catch(e) {
      console.log('Error:', e.message);
    }
  }
}

main();
