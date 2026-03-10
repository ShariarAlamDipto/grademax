const { S3Client, ListBucketsCommand, PutObjectCommand, HeadBucketCommand } = require('@aws-sdk/client-s3');

const ACCOUNT_ID = 'REDACTED';
const ACCESS_KEY = 'REDACTED';
const SECRET_KEY = 'REDACTED';

async function main() {
  const r2 = new S3Client({
    region: 'auto',
    endpoint: `https://${ACCOUNT_ID}.r2.cloudflarestorage.com`,
    credentials: {
      accessKeyId: ACCESS_KEY,
      secretAccessKey: SECRET_KEY,
    },
  });

  // Step 1: List buckets
  console.log('Step 1: Listing buckets...');
  try {
    const { Buckets } = await r2.send(new ListBucketsCommand({}));
    console.log('  Buckets found:', Buckets?.map(b => b.Name));
  } catch (e) {
    console.log('  ListBuckets error:', e.Code || e.name, '-', e.message);
    console.log('  (This may be OK if the token only has object-level permissions)');
  }

  // Step 2: Try common bucket names
  const candidates = ['grademax-papers', 'grademax', 'past-papers', 'papers'];
  console.log('\nStep 2: Testing bucket access...');
  for (const bucket of candidates) {
    try {
      await r2.send(new HeadBucketCommand({ Bucket: bucket }));
      console.log(`  ✓ Bucket "${bucket}" EXISTS and accessible`);
    } catch (e) {
      const code = e.$metadata?.httpStatusCode;
      if (code === 404) {
        console.log(`  ✗ "${bucket}" - does not exist`);
      } else if (code === 403) {
        console.log(`  ? "${bucket}" - access denied`);
      } else {
        console.log(`  ? "${bucket}" - ${e.name}: ${e.message}`);
      }
    }
  }

  // Step 3: Try uploading a test file
  console.log('\nStep 3: Test upload to "grademax-papers"...');
  try {
    await r2.send(new PutObjectCommand({
      Bucket: 'grademax-papers',
      Key: '_test/ping.txt',
      Body: Buffer.from('R2 test - ' + new Date().toISOString()),
      ContentType: 'text/plain',
    }));
    console.log('  ✓ Upload successful! R2 is working.');
    console.log('  Public: https://pub-b96af5a8f7044337bcb17a51b3fd4a60.r2.dev/_test/ping.txt');
  } catch (e) {
    const code = e.$metadata?.httpStatusCode;
    console.log(`  ✗ Upload failed (${code}): ${e.name} - ${e.message}`);
    if (code === 404) {
      console.log('\n  → Bucket "grademax-papers" does not exist.');
      console.log('  → Create it: Cloudflare Dashboard → R2 → Create Bucket → name: grademax-papers');
    } else if (code === 403) {
      console.log('\n  → Access denied. Check your R2 API token permissions.');
      console.log('  → Cloudflare Dashboard → R2 → Manage R2 API Tokens');
      console.log('  → Token needs "Object Read & Write" for this bucket.');
    }
  }
}

main();
