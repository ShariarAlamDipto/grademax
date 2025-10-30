# 📚 GradeMax Classification Rulebook v2.2

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Subject Configuration Specification](#subject-configuration-specification)
4. [Adding a New Subject](#adding-a-new-subject)
5. [Database Schema](#database-schema)
6. [API Integration](#api-integration)
7. [Quality Standards](#quality-standards)
8. [Testing Checklist](#testing-checklist)

---

## Overview

### Purpose
This rulebook defines the standard approach for classifying exam questions across all subjects in GradeMax. Following these rules ensures:
- ✅ Consistent classification quality
- ✅ Easy subject addition/maintenance
- ✅ Backward compatibility
- ✅ Predictable performance
- ✅ Clear debugging paths

### Classification Pipeline
```
Question PDF → Text Extraction → Multi-Pass Classification → Database Update → Worksheet Generation
                                          ↓
                            [Pass 1: LLM Bulk (Gemini)]
                            [Pass 2: LLM Refine (Groq)]
                            [Pass 3: Keywords Fallback]
```

---

## Architecture

### Core Components

#### 1. **Subject-Specific Classifier** (`scripts/{subject}_classifier.py`)
Each subject has its own classifier module with:
- Topic definitions (codes + descriptions)
- Weighted keyword library
- Negative keywords (false positive filters)
- Subject-specific logic

#### 2. **Hybrid Multi-Pass Engine** (`scripts/hybrid_classifier.py`)
Generic classification engine supporting:
- Pass 1: Gemini 2.0 Flash (bulk, fast)
- Pass 2: Groq Llama (refinement)
- Pass 3: Enhanced keywords (fallback)

#### 3. **Runner Scripts** (`scripts/run_{subject}_classification.py`)
Subject-specific runners that:
- Load unclassified pages
- Download and extract PDFs
- Call hybrid classifier
- Update database
- Report statistics

#### 4. **Analysis Tools** (`scripts/analyze_{subject}_classifications.py`)
Quality checkers that:
- Show topic distribution
- Check difficulty balance
- Identify issues
- Generate reports

---

## Subject Configuration Specification

### Required Configuration File: `config/{subject}_topics.yaml`

```yaml
version: "2.2"
subject:
  code: "4PH1"              # Exam board code
  name: "Physics"           # Full name
  board: "Edexcel"          # Exam board
  level: "International GCSE"
  id: "uuid-here"           # Supabase subject_id

schema:
  tag_unit: "question"      # Tag whole questions (not subparts)
  keep_context: true        # Include context in classification
  allow_multi_tag: false    # Single primary topic (set true for multi)
  output_format: "json"

# Topic definitions (minimum 4, maximum 12 recommended)
topics:
  - id: "1"                 # String ID (1-12)
    code: "MOTION"          # Internal code (UPPERCASE)
    name: "Forces & Motion" # Display name
    description: "F=ma, momentum, suvat, energy, terminal velocity, weight"
    
  - id: "2"
    code: "ELEC"
    name: "Electricity"
    description: "V=IR, power, circuits, series/parallel, resistance"
    
  # ... more topics

# Weighted keywords (core classification logic)
keywords:
  core:     # Weight 4-5: Highly specific (formulas, unique phrases)
    topic_1:
      - text: "f=ma"
        weight: 5
      - text: "terminal velocity"
        weight: 5
      - text: "suvat"
        weight: 5
    topic_2:
      - text: "v=ir"
        weight: 5
      - text: "ohm's law"
        weight: 5
        
  support:  # Weight 2-3: Supporting terms (general concepts)
    topic_1:
      - text: "acceleration"
        weight: 3
      - text: "velocity"
        weight: 2
    topic_2:
      - text: "current"
        weight: 2
      - text: "voltage"
        weight: 2

# Negative keywords (avoid false positives)
negatives:
  - "current affairs"       # Don't tag "current" as electricity
  - "radio button"          # Don't tag "radio" as waves/nuclear
  - "power of attorney"     # Don't tag "power" as energy/electricity
  - "subject to change"     # Generic phrases

# Difficulty indicators (optional - used by LLM prompts)
difficulty:
  easy:
    command_words: ["define", "state", "name", "label", "list"]
    characteristics: ["single-step", "recall", "direct substitution"]
    
  medium:
    command_words: ["calculate", "explain", "describe", "compare", "show"]
    characteristics: ["multi-step", "interpretation", "application"]
    
  hard:
    command_words: ["design", "plan", "evaluate", "suggest why", "devise"]
    characteristics: ["synthesis", "evaluation", "unfamiliar context"]

# LLM prompt templates (optional - for advanced customization)
prompts:
  system: |
    You are an expert {board} {level} {subject} examiner.
    Classify questions by their PRIMARY concept being tested.
    
  user_template: |
    Classify this {subject} question into ONE of these topics:
    {topic_list}
    
    Question: {question_text}
    
    Return JSON: {{"topic": "1-{max_topic}", "difficulty": "easy/medium/hard", "confidence": 0.0-1.0}}
```

---

## Adding a New Subject

### Step-by-Step Process

#### **Step 1: Create Subject Configuration**

**File:** `config/{subject}_topics.yaml`

```yaml
version: "2.2"
subject:
  code: "4MA1"
  name: "Mathematics"
  board: "Edexcel"
  level: "International GCSE"
  id: "abc-123-uuid"  # From Supabase subjects table

topics:
  - id: "1"
    code: "NUMBER"
    name: "Number"
    description: "Integers, fractions, decimals, percentages, ratios, proportions"
    
  - id: "2"
    code: "ALGEBRA"
    name: "Algebra"
    description: "Equations, inequalities, sequences, graphs, functions"
    
  # ... 8-10 topics total

keywords:
  core:
    topic_1:
      - text: "hcf"
        weight: 5
      - text: "lcm"
        weight: 5
      - text: "prime factorization"
        weight: 5
    topic_2:
      - text: "solve"
        weight: 4
      - text: "quadratic"
        weight: 5
      - text: "simultaneous equations"
        weight: 5
        
  support:
    topic_1:
      - text: "fraction"
        weight: 2
      - text: "decimal"
        weight: 2
        
negatives:
  - "number of"
  - "in number"
```

#### **Step 2: Create Subject Classifier**

**File:** `scripts/mathematics_classifier.py`

```python
#!/usr/bin/env python3
"""
Mathematics Classifier for GradeMax v2.2
Implements hybrid multi-pass classification for IGCSE Mathematics
"""

import os
import yaml
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass

# Import hybrid classifier base
import sys
sys.path.insert(0, str(Path(__file__).parent))
from hybrid_classifier import HybridClassifier, Classification

SUBJECT_NAME = "Mathematics"
SUBJECT_ID = "abc-123-uuid"  # From Supabase
CONFIG_PATH = Path(__file__).parent.parent / 'config' / 'mathematics_topics.yaml'


class MathematicsClassifier(HybridClassifier):
    """Mathematics-specific classifier extending hybrid base"""
    
    def __init__(self, gemini_key: str = None, groq_key: str = None):
        # Load configuration
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # Build topics dictionary
        self.TOPICS = {
            t['id']: f"{t['name']} ({t['description']})"
            for t in self.config['topics']
        }
        
        # Build weighted keywords from config
        self.WEIGHTED_KEYWORDS = self._build_keywords()
        
        # Build negative keywords
        self.NEGATIVE_KEYWORDS = self.config.get('negatives', [])
        
        # Initialize parent
        super().__init__(gemini_key, groq_key)
        
        print(f"   ✅ {SUBJECT_NAME} classifier initialized")
        print(f"   📚 {len(self.TOPICS)} topics loaded")
        print(f"   🔑 {len(self.WEIGHTED_KEYWORDS)} keywords loaded")
    
    def _build_keywords(self) -> dict:
        """Build weighted keywords from config"""
        keywords = {}
        
        # Core keywords (high weight)
        for topic_id, kw_list in self.config['keywords']['core'].items():
            topic_num = topic_id.replace('topic_', '')
            for kw in kw_list:
                keywords[kw['text']] = (topic_num, kw['weight'])
        
        # Support keywords (lower weight)
        for topic_id, kw_list in self.config['keywords'].get('support', {}).items():
            topic_num = topic_id.replace('topic_', '')
            for kw in kw_list:
                keywords[kw['text']] = (topic_num, kw['weight'])
        
        return keywords


# Test function
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    
    gemini_key = os.getenv('GEMINI_API_KEY')
    groq_key = os.getenv('GROQ_API_KEY')
    
    classifier = MathematicsClassifier(gemini_key, groq_key)
    
    # Test with sample question
    test_q = {
        "number": "1",
        "text": "Solve the quadratic equation x² + 5x + 6 = 0"
    }
    
    result = classifier.classify_keyword_fallback(test_q)
    print(f"\nTest: Topic {result.topic}, {result.difficulty}, {result.confidence:.2f}")
```

#### **Step 3: Create Runner Script**

**File:** `scripts/run_mathematics_classification.py`

```python
#!/usr/bin/env python3
"""
Run Mathematics Classification on All Pages
Uses hybrid multi-pass system
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

sys.path.insert(0, str(Path(__file__).parent))
from mathematics_classifier import MathematicsClassifier, SUBJECT_ID

# Load environment
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

# Initialize
url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
gemini_key = os.getenv('GEMINI_API_KEY')
groq_key = os.getenv('GROQ_API_KEY')

supabase: Client = create_client(url, service_key)

VALID_TOPICS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']  # Adjust to your topic count


def main():
    print("=" * 70)
    print("🚀 MATHEMATICS HYBRID CLASSIFIER")
    print("=" * 70)
    print()
    
    # Initialize classifier
    print("1️⃣  Initializing classifier...")
    classifier = MathematicsClassifier(gemini_key, groq_key)
    print()
    
    # Load papers
    print("2️⃣  Loading Mathematics pages...")
    papers_result = supabase.table('papers').select('*').eq('subject_id', SUBJECT_ID).execute()
    papers = papers_result.data
    print(f"   ✅ Found {len(papers)} papers")
    
    # Get pages
    all_pages = supabase.table('pages').select('*').in_('paper_id', [p['id'] for p in papers]).eq('is_question', True).execute()
    pages = all_pages.data
    print(f"   📊 Total pages: {len(pages)}")
    
    # TODO: Implement classification loop (same as physics)
    # See run_hybrid_classification.py for reference
    
    print("\n✅ Classification complete!")


if __name__ == '__main__':
    main()
```

#### **Step 4: Create Analysis Script**

**File:** `scripts/analyze_mathematics_classifications.py`

```python
#!/usr/bin/env python3
"""Analyze Mathematics classification quality"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from collections import Counter

env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

SUBJECT_ID = "abc-123-uuid"  # Mathematics

url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase = create_client(url, service_key)

# Get pages
papers = supabase.table('papers').select('id').eq('subject_id', SUBJECT_ID).execute()
paper_ids = [p['id'] for p in papers.data]
pages = supabase.table('pages').select('topics, difficulty').in_('paper_id', paper_ids).eq('is_question', True).execute()

print("=" * 70)
print("📊 MATHEMATICS CLASSIFICATION ANALYSIS")
print("=" * 70)
print()

# Analysis logic (same as physics)
# ...
```

#### **Step 5: Update Database (if needed)**

Ensure the `subjects` table has the new subject:

```sql
INSERT INTO subjects (id, name, code, board, level)
VALUES 
  ('abc-123-uuid', 'Mathematics', '4MA1', 'Edexcel', 'International GCSE');
```

#### **Step 6: Test the Classification**

```bash
# Test classifier in isolation
python scripts/mathematics_classifier.py

# Run classification on all pages
python scripts/run_mathematics_classification.py

# Analyze results
python scripts/analyze_mathematics_classifications.py
```

---

## Database Schema

### Required Tables

#### **subjects**
```sql
CREATE TABLE subjects (
  id UUID PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  code VARCHAR(20) NOT NULL,
  board VARCHAR(50),
  level VARCHAR(50),
  created_at TIMESTAMP DEFAULT NOW()
);
```

#### **papers**
```sql
CREATE TABLE papers (
  id UUID PRIMARY KEY,
  subject_id UUID REFERENCES subjects(id),
  year INTEGER NOT NULL,
  season VARCHAR(20) NOT NULL,
  paper_number VARCHAR(10),
  created_at TIMESTAMP DEFAULT NOW()
);
```

#### **pages**
```sql
CREATE TABLE pages (
  id UUID PRIMARY KEY,
  paper_id UUID REFERENCES papers(id),
  question_number VARCHAR(10) NOT NULL,
  is_question BOOLEAN DEFAULT true,
  qp_page_url TEXT NOT NULL,
  ms_page_url TEXT,
  topics TEXT[] DEFAULT '{}',           -- Array of topic IDs
  difficulty VARCHAR(20),                -- 'easy', 'medium', 'hard'
  confidence FLOAT,                      -- 0.0-1.0 (optional)
  classified_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Indexes (Recommended)
```sql
CREATE INDEX idx_pages_topics ON pages USING GIN(topics);
CREATE INDEX idx_pages_difficulty ON pages(difficulty);
CREATE INDEX idx_pages_paper_id ON pages(paper_id);
CREATE INDEX idx_papers_subject_id ON papers(subject_id);
```

---

## API Integration

### Worksheet Generation Endpoint

**File:** `src/app/api/worksheets/generate-v2/route.ts`

The endpoint should:
1. Accept `subjectId`, `topics[]`, `difficulty`, `yearStart`, `yearEnd`
2. Query pages with matching criteria
3. Return selected pages for PDF generation

**Example Query:**
```typescript
const { data: pages } = await supabase
  .from('pages')
  .select('*, papers(year, season, paper_number)')
  .in('paper_id', paperIds)
  .contains('topics', [topicId])  // Array contains topic
  .eq('difficulty', difficulty)    // Optional filter
  .eq('is_question', true)
  .order('random()')              // Random selection
  .limit(limit);
```

---

## Quality Standards

### Minimum Requirements

#### **Topic Coverage**
- ✅ All pages must have at least one valid topic
- ✅ Topic IDs must be strings ('1', '2', ... '12')
- ✅ No invalid topic codes in database

#### **Difficulty Distribution**
- 🎯 **Target:** 20% easy, 60% medium, 20% hard
- ⚠️ **Warning if:** >80% any single difficulty
- ❌ **Error if:** 100% same difficulty

#### **Confidence Scores**
- ✅ **High quality:** >70% pages with confidence ≥0.70
- ⚠️ **Medium quality:** 50-70% pages with confidence ≥0.70
- ❌ **Low quality:** <50% pages with confidence ≥0.70

#### **Topic Balance**
- ✅ **Balanced:** Max/min ratio < 3:1
- ⚠️ **Unbalanced:** Max/min ratio 3-5:1
- ❌ **Severely unbalanced:** Max/min ratio >5:1

### Validation Script Template

**File:** `scripts/validate_{subject}_classifications.py`

```python
#!/usr/bin/env python3
"""Validate classification quality against standards"""

def validate_classifications(subject_id: str):
    # Load pages
    pages = load_pages(subject_id)
    
    # Check 1: Coverage
    assert all(p.get('topics') for p in pages), "Missing topics"
    
    # Check 2: Valid topic IDs
    valid_ids = ['1', '2', '3', '4', '5', '6', '7', '8']
    for p in pages:
        assert all(t in valid_ids for t in p['topics']), f"Invalid topic: {p['topics']}"
    
    # Check 3: Difficulty distribution
    diff_counts = Counter(p['difficulty'] for p in pages)
    max_pct = max(diff_counts.values()) / len(pages)
    assert max_pct < 0.80, f"Difficulty too concentrated: {max_pct:.1%}"
    
    # Check 4: Topic balance
    topic_counts = Counter()
    for p in pages:
        topic_counts.update(p['topics'])
    
    max_count = max(topic_counts.values())
    min_count = min(topic_counts.values())
    ratio = max_count / min_count
    
    if ratio > 5:
        print(f"❌ FAIL: Topic ratio {ratio:.1f}:1 (should be <5:1)")
        return False
    elif ratio > 3:
        print(f"⚠️  WARNING: Topic ratio {ratio:.1f}:1 (should be <3:1)")
    
    print("✅ All quality checks passed")
    return True
```

---

## Testing Checklist

### Pre-Deployment Checklist

#### **Configuration**
- [ ] `config/{subject}_topics.yaml` created
- [ ] All topics have unique IDs (1-12)
- [ ] Topic descriptions are clear
- [ ] Core keywords cover main formulas/concepts
- [ ] Support keywords added
- [ ] Negative keywords identified
- [ ] Subject ID matches Supabase

#### **Classifier**
- [ ] `scripts/{subject}_classifier.py` created
- [ ] Inherits from `HybridClassifier`
- [ ] Loads config correctly
- [ ] Keywords parse successfully
- [ ] Test classification runs without errors

#### **Runner**
- [ ] `scripts/run_{subject}_classification.py` created
- [ ] Connects to Supabase
- [ ] Loads correct subject_id
- [ ] Handles PDF download/extraction
- [ ] Updates database correctly
- [ ] Reports statistics

#### **Analysis**
- [ ] `scripts/analyze_{subject}_classifications.py` created
- [ ] Shows topic distribution
- [ ] Shows difficulty distribution
- [ ] Identifies quality issues

#### **Integration**
- [ ] Subject exists in `subjects` table
- [ ] Papers linked to subject
- [ ] Pages have correct foreign keys
- [ ] Worksheet API recognizes subject
- [ ] Frontend displays new subject

#### **Quality**
- [ ] Run validation script
- [ ] Topic coverage 100%
- [ ] Difficulty distribution reasonable
- [ ] Confidence scores >70% high
- [ ] Topic balance ratio <5:1
- [ ] Sample worksheets generate correctly

---

## Common Pitfalls & Solutions

### Problem: Too Many Keywords Match Multiple Topics

**Solution:** Use negative keywords and increase weight on specific terms
```yaml
# Instead of:
keywords:
  core:
    topic_2:
      - text: "energy"  # Too general
        weight: 3

# Use:
keywords:
  core:
    topic_2:
      - text: "kinetic energy"  # More specific
        weight: 5
      - text: "ek = ½mv²"       # Formula
        weight: 5
        
negatives:
  - "energy drink"
  - "save energy"
```

### Problem: LLM Classifications Are Inconsistent

**Solution:** Improve prompt specificity and examples
```python
prompt = f"""You are an {board} {level} {subject} examiner with 10+ years experience.

CRITICAL: Classify by PRIMARY concept, not vocabulary overlap.

BAD Example:
- Question mentions "energy" → Tagged as "Energy" topic
GOOD Example:
- Question asks "Calculate kinetic energy using KE=½mv²" → "Energy" topic
- Question asks "State energy changes in circuit" → "Electricity" topic

Classify this question..."""
```

### Problem: Difficulty Always Defaults to Medium

**Solution:** Use explicit command word detection
```python
def estimate_difficulty(text: str) -> str:
    text_lower = text.lower()
    
    # Easy indicators (strong signals)
    if any(w in text_lower for w in ["define", "state what is meant by", "give the name"]):
        return "easy"
    
    # Hard indicators (strong signals)
    if any(w in text_lower for w in ["design an experiment", "suggest why", "evaluate"]):
        return "hard"
    
    # Default to medium
    return "medium"
```

### Problem: Rate Limits Hit Frequently

**Solution:** Adjust batch sizes and delays
```python
# For Gemini (1500 RPM free tier)
batch_size = 20
delay = 0.5  # seconds

# For Groq (30 RPM free tier)
batch_size = 1
delay = 2.0  # seconds
```

---

## Version History

### v2.2 (Current)
- Hybrid multi-pass classification
- Enhanced keyword matching with formulas
- Negative keyword filtering
- Weighted scoring system
- Subject-agnostic architecture

### v2.1
- Basic LLM classification
- Simple keyword fallback
- Single-pass approach

### v2.0
- Initial classification system
- Rule-based only

---

## Support & Maintenance

### When Adding Keywords
1. Test on 10-20 sample questions
2. Check for false positives
3. Verify weight is appropriate (5=specific, 2=general)
4. Add negative keywords if needed
5. Re-run classification on subset to verify

### When Adjusting Topics
1. Update `config/{subject}_topics.yaml`
2. Update topic descriptions in classifier
3. Re-run full classification
4. Validate distribution
5. Test worksheet generation

### Monitoring
Run analysis regularly:
```bash
# Weekly check
python scripts/analyze_{subject}_classifications.py

# After major changes
python scripts/validate_{subject}_classifications.py
```

---

## Quick Reference

### File Naming Convention
```
config/
  ├── physics_topics.yaml
  ├── mathematics_topics.yaml
  └── {subject}_topics.yaml

scripts/
  ├── physics_classifier.py
  ├── run_physics_classification.py
  ├── analyze_physics_classifications.py
  ├── mathematics_classifier.py
  ├── run_mathematics_classification.py
  └── analyze_mathematics_classifications.py
```

### Command Templates
```bash
# Test classifier
python scripts/{subject}_classifier.py

# Classify all pages
python scripts/run_{subject}_classification.py

# Check quality
python scripts/analyze_{subject}_classifications.py

# Validate against standards
python scripts/validate_{subject}_classifications.py
```

### Essential Metrics
- **Coverage:** 100% of pages have topics
- **Confidence:** >70% pages have confidence ≥0.70
- **Difficulty:** 20/60/20 split (±10%)
- **Balance:** Topic ratio <3:1 (warn >3:1, error >5:1)

---

## Appendix: Physics Example (Reference Implementation)

See the following files for reference:
- `config/physics_topics.yaml` - Complete configuration
- `scripts/hybrid_classifier.py` - Base classifier engine
- `scripts/run_hybrid_classification.py` - Runner implementation
- `scripts/analyze_classifications.py` - Analysis tool

These files serve as the **gold standard** for implementing new subjects.

---

**Last Updated:** October 23, 2025  
**Version:** 2.2  
**Status:** Production Ready ✅
