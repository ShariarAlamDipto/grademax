# Adding New Subjects - Migration Guide

This guide shows how to add **any new subject** to GradeMax using the established pattern.

## 🎯 Overview

Adding a new subject requires:
1. ✅ Create YAML configuration (topic definitions)
2. ✅ Run database setup (add subject + topics)
3. ✅ Process papers (batch or individual)
4. ✅ Verify in UI (subject appears in dropdown)

**Time**: ~2-3 hours per subject (mostly YAML creation)

## 📋 Step-by-Step Template

### Step 1: Create YAML Configuration

**File**: `config/{subject_name}_topics.yaml`

**Template**:

```yaml
version: 2
subject:
  code: "XXXX"              # e.g., "9MA0", "4MB1", "WME1"
  name: "Subject Full Name"  # e.g., "Mathematics A"
  board: "Edexcel"
  level: "International GCSE"  # or "International A Level"

# Choose ONE of these two modes:

# MODE 1: SIMPLE (like Physics) - Keyword-based
# Just define topics with keywords, no symbol_grammar section

# MODE 2: SYMBOL-AWARE (like Further Pure) - Pattern-based
# Include symbol_grammar section with tokens and methods

# If using Symbol-Aware mode, add:
symbol_grammar:
  normalize:
    superscripts_to_caret: true
    greek_letters_to_ascii_names: true
    minus_to_ascii: true
    times_to_ascii_x: true
    divide_slash: true
  
  tokens:
    # Define patterns for your subject's symbols
    example_token: ["pattern1", "pattern2"]
  
  methods_catalog:
    # Define methods/techniques
    example_method: ["method name", "alternative name"]

schema:
  tag_unit: "question"
  allow_multi_tag: true  # Set false if single-topic only
  output_format: "json"

scoring:
  weights:
    lexical: 0.35      # Adjust based on symbol importance
    symbols: 0.45      # Higher for symbol-heavy subjects
    layout: 0.05
    co_tag_prior: 0.15
  
  penalties:
    negative_hits: -0.22
    too_generic: -0.10

# If using symbol-aware, add hard floors:
symbol_hard_floors:
  TOPIC_ID:
    any_of: ["token1", "token2"]
    min_confidence: 0.62

layout_signals:
  signal_name: ["keyword1", "keyword2"]

# Define topics (adjust count as needed)
topics:
  - id: TOPIC_ID_1        # Uppercase, descriptive
    code: "1"             # Sequential number (string)
    name: "Topic Name"    # Human-readable
    
    # For simple mode:
    keywords: ["word1", "word2", "word3"]
    
    # For symbol-aware mode:
    lexical:
      any: ["word1", "word2", "word3"]
    
    symbols:
      any_sets: ["token1", "token2"]
    
    structural_patterns:
      any: ["regex_pattern1", "regex_pattern2"]
    
    co_tag_prior:
      TOPIC_ID_2: 0.10
      TOPIC_ID_3: 0.05
  
  - id: TOPIC_ID_2
    code: "2"
    name: "Another Topic"
    # ... repeat structure
  
  # Add more topics...

escalation:
  llm_escalation_threshold: 0.62

postprocess:
  negatives_global: ["not", "excluding", "except"]
  ao_mapping:
    TOPIC_ID_1: "Assessment objective 1"
    TOPIC_ID_2: "Assessment objective 2"

output:
  json_schema:
    topics:
      type: array
      items:
        properties:
          id: {type: string}
          confidence: {type: number}
          evidence: {type: array, items: {type: string}}
    methods: {type: array, items: {type: string}}
    dominant_ao: {type: string}
    difficulty_hint: {type: string}
```

### Step 2: Create Database Setup Script

**File**: `scripts/setup_{subject_name}_db.py`

**Template**:

```python
"""
Add {Subject Name} subject and topics to database
Run this ONCE before processing papers
"""

import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from supabase_client import SupabaseClient

load_dotenv('.env.ingest')


def add_subject():
    """Add subject and its topics"""
    db = SupabaseClient()
    config_path = Path('config/{subject_name}_topics.yaml')
    
    if not config_path.exists():
        print(f"❌ Config not found: {config_path}")
        return False
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    subject_info = config['subject']
    topics = config['topics']
    
    print(f"\n{'='*70}")
    print(f"📚 Adding {subject_info['name']} to database")
    print(f"{'='*70}")
    
    # Check if subject exists
    existing = db.client.table('subjects') \
        .select('*') \
        .eq('code', subject_info['code']) \
        .execute()
    
    if existing.data:
        subject_id = existing.data[0]['id']
        print(f"   ✅ Subject already exists (ID: {subject_id})")
    else:
        # Insert subject
        result = db.client.table('subjects').insert({
            'code': subject_info['code'],
            'name': subject_info['name'],
            'board': subject_info['board'],
            'level': subject_info['level']
        }).execute()
        
        if result.data:
            subject_id = result.data[0]['id']
            print(f"   ✅ Subject added (ID: {subject_id})")
        else:
            print(f"   ❌ Failed to add subject")
            return False
    
    # Add topics
    print(f"\n2️⃣  Adding {len(topics)} topics...")
    
    existing_topics = db.client.table('topics') \
        .select('*') \
        .eq('subject_id', subject_id) \
        .execute()
    
    existing_codes = {t['code'] for t in existing_topics.data} if existing_topics.data else set()
    
    added_count = 0
    for topic in topics:
        if topic['code'] in existing_codes:
            print(f"   ⏭️  Topic {topic['code']} already exists")
            continue
        
        # Build description
        description = topic['name']
        if 'lexical' in topic and 'any' in topic['lexical']:
            key_concepts = topic['lexical']['any'][:3]
            if key_concepts:
                description += f" | Includes: {', '.join(key_concepts)}"
        
        # Insert topic
        try:
            result = db.client.table('topics').insert({
                'subject_id': subject_id,
                'code': topic['code'],
                'name': topic['name'],
                'description': description
            }).execute()
            
            if result.data:
                print(f"   ✅ Added topic {topic['code']}: {topic['name']}")
                added_count += 1
        except Exception as e:
            print(f"   ❌ Error adding topic {topic['code']}: {e}")
    
    print(f"\n✅ Setup complete! Added {added_count} topics")
    return True


def verify_setup():
    """Verify the setup"""
    db = SupabaseClient()
    
    # Get subject
    subject = db.client.table('subjects') \
        .select('*') \
        .eq('code', 'XXXX')  # UPDATE THIS
        .execute()
    
    if not subject.data:
        print(f"❌ Subject not found")
        return False
    
    subject_id = subject.data[0]['id']
    print(f"✅ Subject found: {subject.data[0]['name']}")
    
    # Get topics
    topics = db.client.table('topics') \
        .select('*') \
        .eq('subject_id', subject_id) \
        .execute()
    
    print(f"✅ Topics: {len(topics.data)}")
    for topic in sorted(topics.data, key=lambda t: int(t['code']) if t['code'].isdigit() else 999):
        print(f"   {topic['code']}: {topic['name']}")
    
    return True


if __name__ == '__main__':
    if add_subject():
        verify_setup()
        print(f"\n✅ Ready to process papers!")
```

### Step 3: Create Batch Processor

**File**: `scripts/batch_process_{subject_name}.py`

**Template**:

```python
"""
Batch process {Subject Name} papers
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from page_based_ingest import PageBasedPipeline


def find_paper_pairs(raw_dir: Path):
    """Find QP and MS pairs"""
    pairs = []
    
    for year_dir in sorted(raw_dir.glob('*')):
        if not year_dir.is_dir():
            continue
        
        for session_dir in sorted(year_dir.glob('*')):
            if not session_dir.is_dir():
                continue
            
            qp_files = sorted([f for f in session_dir.glob('Paper *.pdf') 
                             if '_MS' not in f.name])
            
            for qp_file in qp_files:
                ms_file = session_dir / f"{qp_file.stem}_MS.pdf"
                if ms_file.exists():
                    pairs.append((qp_file, ms_file))
    
    return pairs


def main():
    """Process all papers"""
    
    RAW_DIR = Path('data/raw/IGCSE/{SubjectFolder}')  # UPDATE THIS
    CONFIG_PATH = 'config/{subject_name}_topics.yaml'  # UPDATE THIS
    SUBJECT_NAME = 'Subject Full Name'  # UPDATE THIS
    
    if not RAW_DIR.exists():
        print(f"❌ Directory not found: {RAW_DIR}")
        return
    
    pairs = find_paper_pairs(RAW_DIR)
    print(f"\n📊 Found {len(pairs)} paper pair(s)")
    
    if not pairs:
        return
    
    pipeline = PageBasedPipeline(config_path=CONFIG_PATH, subject_name=SUBJECT_NAME)
    
    success_count = 0
    for i, (qp_path, ms_path) in enumerate(pairs, 1):
        print(f"\n{'='*70}")
        print(f"📄 Processing pair {i}/{len(pairs)}")
        
        try:
            pipeline.process_paper_pair(str(qp_path), str(ms_path))
            success_count += 1
            print(f"\n✅ Successfully processed {qp_path.name}")
        except Exception as e:
            print(f"\n❌ Failed: {e}")
    
    print(f"\n✅ Processed {success_count}/{len(pairs)} papers")


if __name__ == '__main__':
    main()
```

### Step 4: Update UI (Already Done!)

The UI already includes all subjects in `src/app/generate/page.tsx`:

```typescript
const SUBJECTS = [
  {code: '4PH1', name: 'IGCSE Physics', ...},
  {code: '9MA0', name: 'IGCSE Mathematics A', ...},
  {code: '4MB1', name: 'IGCSE Mathematics B', ...},
  {code: '9FM0', name: 'IGCSE Further Pure Mathematics', ...},
  {code: 'WME1', name: 'IAL Mechanics 1', ...}
];
```

**To add more**: Just add to this array!

### Step 5: Run Setup

```powershell
# 1. Setup database
python scripts/setup_{subject_name}_db.py

# 2. Test (optional)
python scripts/test_classifier.py  # Update with your subject test

# 3. Process papers
python scripts/batch_process_{subject_name}.py

# 4. Verify in UI
# Open /generate → Select your subject
```

## 🎓 Real Examples

### Example 1: Mathematics A (Simple Mode)

**Config**: `config/maths_a_topics.yaml`

```yaml
version: 2
subject:
  code: "9MA0"
  name: "Mathematics A"
  board: "Edexcel"
  level: "International GCSE"

# No symbol_grammar = Simple mode

topics:
  - id: NUMBER
    code: "1"
    name: "Number"
    keywords: ["fraction", "decimal", "percentage", "ratio", "proportion"]
  
  - id: ALGEBRA
    code: "2"
    name: "Algebra"
    keywords: ["equation", "expression", "factorise", "expand", "simplify"]
  
  - id: GEOMETRY
    code: "3"
    name: "Geometry"
    keywords: ["angle", "triangle", "circle", "polygon", "area", "volume"]
  
  # ... more topics
```

### Example 2: IAL Mechanics 1 (Symbol-Aware Mode)

**Config**: `config/mechanics_topics.yaml`

```yaml
version: 2
subject:
  code: "WME1"
  name: "IAL Mechanics 1"
  board: "Edexcel"
  level: "International A Level"

symbol_grammar:
  normalize:
    greek_letters_to_ascii_names: true
  
  tokens:
    vectors: ["\\bi\\b", "\\bj\\b", "position vector"]
    forces: ["\\bN\\b", "Newton", "force"]
    motion: ["\\bm\\b.*s⁻²", "acceleration", "velocity"]
  
  methods_catalog:
    suvat: ["suvat", "equations of motion"]
    resolving: ["resolving forces", "components"]

symbol_hard_floors:
  KINEMATICS:
    any_of: ["motion", "suvat_equations"]
    min_confidence: 0.65

topics:
  - id: KINEMATICS
    code: "1"
    name: "Kinematics"
    lexical:
      any: ["velocity", "acceleration", "displacement", "motion"]
    symbols:
      any_sets: ["motion", "vectors"]
    structural_patterns:
      any: ["v = u \\+ at", "s = ut \\+ .*at²"]
  
  # ... more topics
```

## 📊 Classification Mode Decision

**Use Simple Mode when**:
- ✅ Topics are clearly distinguishable by keywords
- ✅ Subject doesn't have complex mathematical notation
- ✅ Single-topic classification is sufficient
- ✅ Examples: Basic Physics, Chemistry, Biology

**Use Symbol-Aware Mode when**:
- ✅ Mathematical symbols are primary indicators
- ✅ Topics overlap with keywords (need symbol differentiation)
- ✅ Multi-topic classification needed
- ✅ Examples: Further Pure Maths, Mechanics, Complex Maths

## ⚠️ Common Pitfalls

### 1. Topic Code Conflicts
**Problem**: Using same code "1" for different subjects
**Solution**: Codes are scoped by subject_id in database - OK to reuse!

### 2. Regex Errors
**Problem**: Invalid regex patterns crash classifier
**Solution**: Test patterns with `re.compile()` before adding to YAML

### 3. Overfitting to Examples
**Problem**: Patterns too specific, miss valid questions
**Solution**: Use broader patterns, rely on combination of signals

### 4. Forgetting Rate Limits
**Problem**: API rate limit errors during processing
**Solution**: Pipeline has 4.5s delay between questions (already handled)

### 5. Symbol Normalization Issues
**Problem**: Symbols not detected after normalization
**Solution**: Check `normalize` settings match your symbol patterns

## ✅ Validation Checklist

After adding a new subject:

- [ ] YAML config loads without errors
- [ ] Database setup completes successfully
- [ ] Subject appears in `subjects` table
- [ ] All topics appear in `topics` table
- [ ] Test classification on sample question
- [ ] Batch processor finds papers
- [ ] Papers process without errors
- [ ] Questions appear in `pages` table with topics
- [ ] UI dropdown shows subject
- [ ] Topics display in table
- [ ] Worksheet generation works
- [ ] PDF preview works

## 🚀 Quick Reference

**Required files**:
1. `config/{subject}_topics.yaml` - Topic definitions
2. `scripts/setup_{subject}_db.py` - Database setup
3. `scripts/batch_process_{subject}.py` - Batch processor

**Required folders**:
```
data/raw/IGCSE/{Subject}/
  YYYY/
    Session/
      Paper X.pdf
      Paper X_MS.pdf
```

**Commands**:
```powershell
python scripts/setup_{subject}_db.py
python scripts/batch_process_{subject}.py
```

**Time estimate**:
- YAML creation: 1-2 hours
- Scripts: 30 minutes (copy/modify template)
- Testing: 30 minutes
- Processing: ~1 hour per 10 papers

---

## 🎉 You're Ready!

Follow this guide to add **any new subject** to GradeMax. The classifier handles both simple and symbol-aware modes automatically!

**Questions?** Check:
- `docs/FURTHER_PURE_SETUP.md` - Detailed setup guide
- `docs/ARCHITECTURE.md` - System architecture
- `docs/QUICK_REFERENCE.md` - Command reference
