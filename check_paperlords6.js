const https = require('https');

const SUPABASE_URL = 'https://lldrclumayqoegzfxdcb.supabase.co';
const ANON_KEY = 'REDACTED';

function supabaseGet(table, params = '') {
  return new Promise((resolve, reject) => {
    const url = `${SUPABASE_URL}/rest/v1/${table}?${params}`;
    const req = https.get(url, {
      headers: {
        'apikey': ANON_KEY,
        'Authorization': `Bearer ${ANON_KEY}`,
        'Content-Type': 'application/json',
        'Prefer': 'count=exact'
      }
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const count = res.headers['content-range'];
          resolve({ status: res.statusCode, data: JSON.parse(data), count });
        } catch(e) {
          resolve({ status: res.statusCode, data: data.substring(0, 500), count: null });
        }
      });
    });
    req.on('error', reject);
  });
}

async function main() {
  // 1. Get schema/table info
  console.log('=== Checking papers table structure ===\n');
  
  // Get first 3 papers to see the schema
  const sample = await supabaseGet('papers', 'select=*&limit=3&category=eq.IGCSE&deleted_at=is.null');
  console.log('Status:', sample.status);
  console.log('Content-Range:', sample.count);
  
  if (sample.status === 200 && Array.isArray(sample.data)) {
    console.log('Sample count:', sample.data.length);
    if (sample.data.length > 0) {
      console.log('\n--- Paper Schema (columns) ---');
      console.log(Object.keys(sample.data[0]));
      console.log('\n--- Sample Papers ---');
      sample.data.forEach((p, i) => {
        console.log(`\nPaper ${i + 1}:`, JSON.stringify(p, null, 2));
      });
    }
  } else {
    console.log('Response:', sample.data);
  }
  
  // 2. Count total IGCSE papers
  console.log('\n\n=== Counting all papers ===');
  const igcseCount = await supabaseGet('papers', 'select=id&category=eq.IGCSE&deleted_at=is.null&limit=1');
  console.log('IGCSE papers count:', igcseCount.count);
  
  const ialCount = await supabaseGet('papers', 'select=id&category=eq.IAL&deleted_at=is.null&limit=1');
  console.log('IAL papers count:', ialCount.count);
  
  // 3. Get unique subjects
  console.log('\n\n=== Unique subjects ===');
  const allPapers = await supabaseGet('papers', 'select=subject,category&deleted_at=is.null&limit=20000');
  if (Array.isArray(allPapers.data)) {
    const subjects = {};
    allPapers.data.forEach(p => {
      const key = `${p.category} - ${p.subject}`;
      subjects[key] = (subjects[key] || 0) + 1;
    });
    Object.entries(subjects).sort(([,a],[,b]) => b - a).forEach(([k, v]) => {
      console.log(`  ${k}: ${v} papers`);
    });
    console.log(`\nTotal papers: ${allPapers.data.length}`);
  }
  
  // 4. Get a full paper record with download URL
  console.log('\n\n=== Paper with download URL ===');
  const physPaper = await supabaseGet('papers', 'select=*&category=eq.IGCSE&subject=ilike.*physics*&deleted_at=is.null&limit=5');
  if (Array.isArray(physPaper.data)) {
    physPaper.data.forEach((p, i) => {
      console.log(`\nPhysics Paper ${i + 1}:`);
      console.log('  Subject:', p.subject);
      console.log('  Title:', p.title || p.name);
      console.log('  Year:', p.year);
      console.log('  Type:', p.type);
      console.log('  URL:', p.url || p.file_url || p.download_url || p.pdf_url);
      // Show all fields with URLs
      Object.entries(p).forEach(([k, v]) => {
        if (typeof v === 'string' && (v.includes('http') || v.includes('.pdf'))) {
          console.log(`  ${k}: ${v}`);
        }
      });
    });
  }
  
  // 5. Check store_settings for any useful config
  console.log('\n\n=== Store settings ===');
  const settings = await supabaseGet('store_settings', 'select=*&limit=1');
  if (Array.isArray(settings.data) && settings.data.length > 0) {
    const s = settings.data[0];
    // Only show relevant fields
    const relevant = Object.entries(s).filter(([k]) => 
      k.includes('paper') || k.includes('igcse') || k.includes('ial') || k.includes('download') || k.includes('storage')
    );
    if (relevant.length > 0) {
      console.log('Relevant settings:', Object.fromEntries(relevant));
    }
    console.log('All setting keys:', Object.keys(s));
  }
}

main().catch(console.error);
