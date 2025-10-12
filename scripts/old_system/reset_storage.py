"""
Reset only the pdfs_uploaded flag in manifest
"""
import json
from pathlib import Path

manifest_path = Path("data/processed/4PH1_2019_Jun_1P/manifest.json")

with open(manifest_path, 'r', encoding='utf-8') as f:
    manifest = json.load(f)

# Reset PDF upload flag
manifest['processing']['pdfs_uploaded'] = False
manifest['processing']['stored_in_db'] = False

with open(manifest_path, 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

print("✅ Reset pdfs_uploaded and stored_in_db flags")
print(f"   Manifest: {manifest_path}")
