#!/usr/bin/env python3
"""
Detailed audit of Supabase question-pdfs + lectures buckets to identify what
can be safely deleted vs what is actively referenced.

Categorisation per folder/file:

  KEEP                 - DB references this exact path (qp_page_url or ms_page_url).
                         Or, after Bio/Chem case-fix, the DB will reference it.
                         => Do not delete.

  ORPHAN_SAFE          - Storage has it, no DB row references it (even after the
                         Bio/Chem case-fix). Safe to delete.
                         Includes Physics old-format duplicates (e.g. 2011_Jun_1P
                         when DB references 2011_May-Jun_P1).

  ORPHAN_REVIEW        - Storage has it, no DB ref, BUT a similar-named DB-referenced
                         folder is *missing* from storage. Could be a misnamed
                         alternative — review before deleting.
                         (Typical case: MathsB folders without R-suffix when DB
                         references R-suffix variants.)

  MISSING_FROM_STORAGE - DB references this path but storage has no folder there.
                         The question card will appear in Test Builder but its
                         PDF will fail to load. Doesn't take space, but flagged.

Outputs:
  audit_cleanup_report.txt   - Human-readable report
  cleanup_safe_delete.txt    - One file path per line, ORPHAN_SAFE only
  cleanup_review.txt         - ORPHAN_REVIEW for manual decision
  cleanup_missing.txt        - MISSING_FROM_STORAGE (informational)

Usage:
    python -X utf8 scripts/audit_for_cleanup.py
"""

import os
import re
import sys
from collections import defaultdict
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv(".env.local")

from supabase import create_client

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

QP_BUCKET = "question-pdfs"
LEC_BUCKET = "lectures"
QP_BASE = f"{SUPABASE_URL}/storage/v1/object/public/{QP_BUCKET}/"
LEC_BASE = f"{SUPABASE_URL}/storage/v1/object/public/{LEC_BUCKET}/"

# ── Bio/Chem case-fix regex (matches what migrate_storage_to_r2.py does) ────
SEASON_RE = re.compile(r"(/pages/\d{4}_)([a-z][a-z\-]*)(_)")

def apply_case_fix(path: str) -> str:
    """For Biology/Chemistry: title-case the season segment."""
    if "/Biology/" not in path and "/Chemistry/" not in path:
        return path
    return SEASON_RE.sub(
        lambda m: f"{m.group(1)}{m.group(2).title()}{m.group(3)}",
        path,
    )

# ── Walk storage with sizes ──────────────────────────────────────────────────
def walk_bucket(bucket: str, prefix: str = "") -> list[dict]:
    """Returns list of {path, size_bytes, folder} for every file."""
    results = []
    try:
        items = supabase.storage.from_(bucket).list(prefix, {"limit": 1000})
    except Exception as e:
        print(f"  ERROR listing {bucket}/{prefix}: {e}")
        return results
    for item in items:
        full = f"{prefix}/{item['name']}" if prefix else item["name"]
        if item.get("id") is None:
            results.extend(walk_bucket(bucket, full))
        else:
            size = (item.get("metadata") or {}).get("size", 0) or 0
            results.append({
                "path": full,
                "size": size,
                "folder": "/".join(full.split("/")[:-1]),
            })
    return results

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Load DB-referenced paths (with case-fix applied)
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 78)
print("GRADEMAX STORAGE CLEANUP AUDIT")
print("=" * 78)
print("\n[1] Loading DB references (pages.qp_page_url + ms_page_url)...")

db_paths_qp: set[str] = set()      # what DB currently has
db_paths_fixed: set[str] = set()   # what DB would have AFTER case-fix
offset = 0
while True:
    resp = (supabase.table("pages")
            .select("qp_page_url, ms_page_url")
            .range(offset, offset + 999).execute())
    rows = resp.data or []
    if not rows: break
    for row in rows:
        for col in ("qp_page_url", "ms_page_url"):
            url = row.get(col)
            if not url: continue
            if url.startswith(QP_BASE):
                path = url.split(QP_BASE, 1)[1]
                db_paths_qp.add(path)
                db_paths_fixed.add(apply_case_fix(path))
    if len(rows) < 1000: break
    offset += 1000

print(f"    DB references {len(db_paths_qp):,} unique storage paths "
      f"(question-pdfs bucket)")
case_fixes = len(db_paths_fixed - db_paths_qp)
print(f"    Bio/Chem case-fix would adjust {case_fixes:,} paths")

# Lectures (separate logic — references stored in lectures.file_url)
db_lecture_paths: set[str] = set()
try:
    offset = 0
    while True:
        resp = (supabase.table("lectures")
                .select("file_url")
                .range(offset, offset + 999).execute())
        rows = resp.data or []
        if not rows: break
        for row in rows:
            url = row.get("file_url") or ""
            if url.startswith(LEC_BASE):
                db_lecture_paths.add(url.split(LEC_BASE, 1)[1])
        if len(rows) < 1000: break
        offset += 1000
    print(f"    DB references {len(db_lecture_paths):,} lecture files")
except Exception as e:
    print(f"    (lectures table check skipped: {e})")

# Folders the DB references (after fix)
db_folders_fixed = {"/".join(p.split("/")[:-1]) for p in db_paths_fixed}

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Walk storage with sizes
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2] Walking question-pdfs bucket (this may take a minute)...")
qp_files = walk_bucket(QP_BUCKET)
print(f"    Found {len(qp_files):,} files")

print("\n[3] Walking lectures bucket...")
lec_files = walk_bucket(LEC_BUCKET)
print(f"    Found {len(lec_files):,} files")

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Categorise question-pdfs files
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4] Categorising question-pdfs files...")

# Aggregate by folder for cleaner reporting
folder_stats: dict[str, dict] = defaultdict(lambda: {
    "files": 0, "size": 0, "subject": "_unknown", "category": None
})

storage_folders: dict[str, set[str]] = defaultdict(set)  # subject -> folder names
for f in qp_files:
    folder = f["folder"]
    parts = folder.split("/")
    subject = parts[1] if len(parts) >= 4 and parts[0] == "subjects" else "_other"
    folder_name = parts[3] if len(parts) >= 4 else folder
    storage_folders[subject].add(folder_name)
    folder_stats[folder]["files"] += 1
    folder_stats[folder]["size"] += f["size"]
    folder_stats[folder]["subject"] = subject

# DB-expected folders per subject (post case-fix)
db_folders_by_subj: dict[str, set[str]] = defaultdict(set)
for p in db_folders_fixed:
    parts = p.split("/")
    if len(parts) >= 4 and parts[0] == "subjects":
        db_folders_by_subj[parts[1]].add(parts[3])

# Categorise each storage file
safe_delete: list[dict] = []
review: list[dict] = []
keep_files = 0
keep_size = 0

for f in qp_files:
    fixed_path = apply_case_fix(f["path"])
    if fixed_path in db_paths_fixed:
        keep_files += 1
        keep_size += f["size"]
        continue

    parts = f["folder"].split("/")
    subject = parts[1] if len(parts) >= 4 else "_other"
    folder_name = parts[3] if len(parts) >= 4 else f["folder"]

    # Is there a similar-named missing folder? -> ORPHAN_REVIEW
    db_folders_for_subj = db_folders_by_subj.get(subject, set())
    storage_folders_for_subj = storage_folders.get(subject, set())
    missing_folders = db_folders_for_subj - storage_folders_for_subj

    has_similar_missing = False
    for miss in missing_folders:
        # Case-insensitive substring match in either direction
        if folder_name.lower() in miss.lower() or miss.lower() in folder_name.lower():
            has_similar_missing = True
            break

    if has_similar_missing:
        review.append({**f, "subject": subject, "folder_name": folder_name})
    else:
        safe_delete.append({**f, "subject": subject, "folder_name": folder_name})

# Folders the DB expects but storage has nothing for
missing_paths = db_paths_fixed - {apply_case_fix(f["path"]) for f in qp_files}

# Lectures
lec_keep = lec_orphan = 0
lec_keep_size = lec_orphan_size = 0
lec_safe_delete: list[dict] = []
for f in lec_files:
    if f["path"] in db_lecture_paths:
        lec_keep += 1
        lec_keep_size += f["size"]
    else:
        lec_orphan += 1
        lec_orphan_size += f["size"]
        lec_safe_delete.append(f)

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Per-subject summary
# ─────────────────────────────────────────────────────────────────────────────
def fmt(b): return f"{b/1024/1024:>7.1f} MB" if b else "      0"

print("\n" + "=" * 78)
print("PER-SUBJECT BREAKDOWN (question-pdfs)")
print("=" * 78)

subject_stats = defaultdict(lambda: {
    "keep_f": 0, "keep_b": 0,
    "del_f": 0,  "del_b": 0,
    "rev_f": 0,  "rev_b": 0,
})

for f in qp_files:
    parts = f["folder"].split("/")
    subj = parts[1] if len(parts) >= 4 else "_other"
    if apply_case_fix(f["path"]) in db_paths_fixed:
        subject_stats[subj]["keep_f"] += 1
        subject_stats[subj]["keep_b"] += f["size"]

for f in safe_delete:
    s = subject_stats[f["subject"]]
    s["del_f"] += 1
    s["del_b"] += f["size"]
for f in review:
    s = subject_stats[f["subject"]]
    s["rev_f"] += 1
    s["rev_b"] += f["size"]

header = f"  {'Subject':18s}  {'KEEP':>14s}  {'SAFE DELETE':>14s}  {'REVIEW':>14s}"
print(header)
print("  " + "-" * (len(header) - 2))
total_keep_b = total_del_b = total_rev_b = 0
for subj in sorted(subject_stats):
    s = subject_stats[subj]
    total_keep_b += s["keep_b"]
    total_del_b += s["del_b"]
    total_rev_b += s["rev_b"]
    print(f"  {subj:18s}  "
          f"{s['keep_f']:>4d}f {fmt(s['keep_b'])}  "
          f"{s['del_f']:>4d}f {fmt(s['del_b'])}  "
          f"{s['rev_f']:>4d}f {fmt(s['rev_b'])}")

print("  " + "-" * (len(header) - 2))
print(f"  {'TOTAL':18s}  "
      f"{keep_files:>4d}f {fmt(total_keep_b)}  "
      f"{len(safe_delete):>4d}f {fmt(total_del_b)}  "
      f"{len(review):>4d}f {fmt(total_rev_b)}")

# Lecture summary
print("\n" + "=" * 78)
print("LECTURES BUCKET")
print("=" * 78)
print(f"  KEEP        : {lec_keep:>4d} files  {fmt(lec_keep_size)}")
print(f"  SAFE DELETE : {lec_orphan:>4d} files  {fmt(lec_orphan_size)}")

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Show example folders per category for transparency
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 78)
print("EXAMPLES OF SAFE-TO-DELETE FOLDERS (per subject, top 5)")
print("=" * 78)

safe_by_folder: dict[str, dict] = defaultdict(lambda: {"files": 0, "size": 0, "subject": ""})
for f in safe_delete:
    safe_by_folder[f["folder"]]["files"] += 1
    safe_by_folder[f["folder"]]["size"] += f["size"]
    safe_by_folder[f["folder"]]["subject"] = f["subject"]

by_subject_folders: dict[str, list] = defaultdict(list)
for folder, data in safe_by_folder.items():
    by_subject_folders[data["subject"]].append((folder, data))

for subj in sorted(by_subject_folders):
    folders = sorted(by_subject_folders[subj], key=lambda x: -x[1]["size"])
    if not folders: continue
    print(f"\n  {subj}:")
    for folder, data in folders[:5]:
        folder_short = folder.replace(f"subjects/{subj}/pages/", "")
        print(f"    {folder_short:35s}  {data['files']:>3d} files  {fmt(data['size'])}")
    if len(folders) > 5:
        rest_size = sum(d["size"] for _, d in folders[5:])
        print(f"    ... and {len(folders)-5} more folders ({fmt(rest_size)})")

# Review category (needs human eye)
if review:
    print("\n" + "=" * 78)
    print("ORPHAN_REVIEW — folders with similar-named missing-from-storage twins")
    print("=" * 78)
    print("(Could be a renamed alternative — manually verify before deleting)\n")
    review_by_folder: dict[str, dict] = defaultdict(lambda: {"files": 0, "size": 0, "subject": ""})
    for f in review:
        review_by_folder[f["folder"]]["files"] += 1
        review_by_folder[f["folder"]]["size"] += f["size"]
        review_by_folder[f["folder"]]["subject"] = f["subject"]

    review_subj_folders: dict[str, list] = defaultdict(list)
    for folder, data in review_by_folder.items():
        review_subj_folders[data["subject"]].append((folder, data))

    for subj in sorted(review_subj_folders):
        print(f"  {subj}:")
        # Show what missing DB folders look like vs what storage has
        db_for_subj = db_folders_by_subj.get(subj, set())
        st_for_subj = storage_folders.get(subj, set())
        missing = sorted(db_for_subj - st_for_subj)[:5]
        if missing:
            print(f"    DB expects (but storage missing): {missing}")
        for folder, data in sorted(review_subj_folders[subj], key=lambda x: -x[1]["size"])[:5]:
            short = folder.replace(f"subjects/{subj}/pages/", "")
            print(f"    storage has: {short:30s}  {data['files']:>3d} files  {fmt(data['size'])}")
        print()

# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Missing-from-storage (DB has URL but no file)
# ─────────────────────────────────────────────────────────────────────────────
if missing_paths:
    print("=" * 78)
    print(f"MISSING_FROM_STORAGE — {len(missing_paths):,} DB rows reference paths that don't exist")
    print("=" * 78)
    print("(These take no space, but the questions will appear with broken PDFs.)\n")
    missing_by_subj: dict[str, list] = defaultdict(list)
    for p in missing_paths:
        parts = p.split("/")
        subj = parts[1] if len(parts) >= 4 and parts[0] == "subjects" else "_other"
        missing_by_subj[subj].append(p)
    for subj in sorted(missing_by_subj):
        print(f"  {subj}: {len(missing_by_subj[subj])} missing files")
        for p in sorted(missing_by_subj[subj])[:3]:
            print(f"    {p}")

# ─────────────────────────────────────────────────────────────────────────────
# Step 7: Write deletion lists
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 78)
print("WRITING DELETION LISTS")
print("=" * 78)

with open("cleanup_safe_delete.txt", "w", encoding="utf-8") as f:
    f.write(f"# question-pdfs orphans: {len(safe_delete)} files, {total_del_b/1024/1024:.1f} MB\n")
    f.write(f"# Format: bucket\\tpath\\tsize_bytes\n")
    for item in sorted(safe_delete, key=lambda x: x["path"]):
        f.write(f"{QP_BUCKET}\t{item['path']}\t{item['size']}\n")
    f.write(f"\n# lectures orphans: {len(lec_safe_delete)} files\n")
    for item in lec_safe_delete:
        f.write(f"{LEC_BUCKET}\t{item['path']}\t{item['size']}\n")

with open("cleanup_review.txt", "w", encoding="utf-8") as f:
    f.write(f"# Files whose deletion needs manual review: {len(review)}, {total_rev_b/1024/1024:.1f} MB\n")
    f.write(f"# Format: bucket\\tpath\\tsize_bytes\n")
    for item in sorted(review, key=lambda x: x["path"]):
        f.write(f"{QP_BUCKET}\t{item['path']}\t{item['size']}\n")

with open("cleanup_missing.txt", "w", encoding="utf-8") as f:
    f.write(f"# DB rows reference these paths but storage has no file: {len(missing_paths)}\n")
    for p in sorted(missing_paths):
        f.write(f"{p}\n")

print(f"  cleanup_safe_delete.txt : {len(safe_delete) + len(lec_safe_delete):>5d} files  "
      f"{(total_del_b + lec_orphan_size)/1024/1024:>6.1f} MB")
print(f"  cleanup_review.txt      : {len(review):>5d} files  {total_rev_b/1024/1024:>6.1f} MB")
print(f"  cleanup_missing.txt     : {len(missing_paths):>5d} paths (DB-only, no space)")

# ─────────────────────────────────────────────────────────────────────────────
# Final summary
# ─────────────────────────────────────────────────────────────────────────────
total_storage = total_keep_b + total_del_b + total_rev_b + lec_keep_size + lec_orphan_size
print("\n" + "=" * 78)
print("BOTTOM LINE")
print("=" * 78)
print(f"  Current Supabase storage   : {total_storage/1024/1024:>7.1f} MB"
      f" ({total_storage/1024/1024/1000:.1%} of 1 GB free tier)")
print(f"  Reclaimable now (SAFE)     : {(total_del_b + lec_orphan_size)/1024/1024:>7.1f} MB"
      f"  -> after delete: {(total_storage - total_del_b - lec_orphan_size)/1024/1024:.0f} MB")
print(f"  Reclaimable if REVIEW ok   : {total_rev_b/1024/1024:>7.1f} MB"
      f"  -> after delete: "
      f"{(total_storage - total_del_b - total_rev_b - lec_orphan_size)/1024/1024:.0f} MB")
print(f"  Must keep (DB-referenced)  : {(total_keep_b + lec_keep_size)/1024/1024:>7.1f} MB")

free_tier = 1024 * 1024 * 1024
under_after_safe = (total_storage - total_del_b - lec_orphan_size) <= free_tier
under_after_all = (total_keep_b + lec_keep_size) <= free_tier
print()
print(f"  Under 1 GB after SAFE-only deletes? "
      f"{'YES' if under_after_safe else 'NO  -> still need R2 migration to fit free tier'}")
print(f"  Under 1 GB if you delete everything reclaimable? "
      f"{'YES' if under_after_all else 'NO  -> R2 migration is the only path'}")
print("=" * 78)

print("""
NEXT STEPS:
  1. Review cleanup_safe_delete.txt and cleanup_review.txt
  2. Decide which to delete (start with safe_delete only)
  3. Run:  python -X utf8 scripts/execute_cleanup.py cleanup_safe_delete.txt --dry-run
     then: python -X utf8 scripts/execute_cleanup.py cleanup_safe_delete.txt
""")
