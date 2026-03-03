const https = require('https');

function fetch(url, headers = {}) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : require('http');
    const req = client.get(url, {
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
      res.on('end', () => resolve({ status: res.status || res.statusCode, headers: res.headers, body: data }));
    });
    req.on('error', reject);
  });
}

async function main() {
  // The site uses Supabase client-side. Let's find the Supabase URL from JS chunks.
  // The main app chunk should contain the supabase createClient call with URL + anon key.
  
  console.log('=== Finding Supabase credentials from JS chunks ===\n');
  
  // Get the main page and find script references
  const page = await fetch('https://www.paperlords.org/');
  
  // Get the list of JS chunks
  const scriptRegex = /src="(\/_next\/static\/chunks\/[^"]+\.js)"/g;
  const scripts = [];
  let m;
  while ((m = scriptRegex.exec(page.body)) !== null) {
    scripts.push(m[1]);
  }
  console.log('JS chunks found:', scripts.length);
  
  // Search each chunk for supabase URL pattern
  for (const script of scripts) {
    const js = await fetch('https://www.paperlords.org' + script);
    if (js.body.includes('supabase') || js.body.includes('SUPABASE') || js.body.includes('.supabase.co')) {
      console.log(`\n>>> ${script} contains supabase reference`);
      
      // Find supabase URL
      const urlMatch = js.body.match(/https:\/\/[a-z0-9]+\.supabase\.co/);
      if (urlMatch) console.log('Supabase URL:', urlMatch[0]);
      
      // Find anon key
      const keyMatch = js.body.match(/eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/);
      if (keyMatch) console.log('Anon Key:', keyMatch[0]);
      
      // Find all supabase references
      const supaMatches = js.body.match(/[a-z0-9]+\.supabase\.co[^\s"']*/g);
      if (supaMatches) console.log('Supabase refs:', [...new Set(supaMatches)]);
      
      // Show context around supabase
      const idx = js.body.indexOf('supabase');
      if (idx > -1) {
        const start = Math.max(0, idx - 200);
        const end = Math.min(js.body.length, idx + 500);
        console.log('Context:', js.body.substring(start, end));
      }
    }
  }
  
  // Also check environment variable patterns in chunks
  console.log('\n\n=== Looking for env vars in page HTML ===');
  const envMatches = page.body.match(/NEXT_PUBLIC_[A-Z_]+|process\.env\.[A-Z_]+/g);
  console.log('Env vars:', [...new Set(envMatches || [])]);
  
  // Check for inline __ENV or config
  const configMatch = page.body.match(/window\.__[A-Z_]+\s*=\s*\{[^}]+\}/g);
  console.log('Window configs:', configMatch);
}

main().catch(console.error);
