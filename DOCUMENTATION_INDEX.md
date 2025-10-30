# 📚 GradeMax Classification System - Documentation Index

## Overview

The GradeMax classification system uses a hybrid multi-pass approach to automatically classify exam questions by topic and difficulty. This documentation provides everything you need to understand, use, and extend the system.

---

## 📖 Core Documentation

### 1. **CLASSIFICATION_RULEBOOK.md** 
**The Complete Specification**

- Full architecture explanation
- Subject configuration specification  
- Database schema requirements
- Quality standards and validation
- Testing procedures
- Troubleshooting guide

**Use when:** You need to understand how the system works or need reference material

**Link:** [`CLASSIFICATION_RULEBOOK.md`](./CLASSIFICATION_RULEBOOK.md)

---

### 2. **QUICK_START_NEW_SUBJECT.md**
**Step-by-Step Implementation Guide**

- 10-step process to add new subjects (~1 hour)
- Code examples and templates
- Testing and validation procedures
- Common pitfalls and solutions
- Time estimates for each step

**Use when:** You're adding a new subject to the system

**Link:** [`QUICK_START_NEW_SUBJECT.md`](./QUICK_START_NEW_SUBJECT.md)

---

### 3. **CLASSIFICATION_UPGRADE.md**
**v2.2 Upgrade Summary**

- What changed from v2.0 → v2.2
- Performance improvements (3x faster, 5x more accurate)
- New features (formula recognition, negative keywords)
- Current status of Physics classification
- Files created and their purposes

**Use when:** You need to understand what was improved and why

**Link:** [`CLASSIFICATION_UPGRADE.md`](./CLASSIFICATION_UPGRADE.md)

---

### 4. **UPGRADE_V23.md** ⭐ NEW
**v2.3 Upgrade - Latest Version**

- Groq Llama 3.3 70B (replaced Gemini - no rate limits!)
- 4000 char context (was 2000) for better accuracy
- Page context extraction for incomplete questions
- Disambiguation rules and postprocessing
- Complete setup and testing guide

**Use when:** You want the latest and best classification system

**Link:** [`UPGRADE_V23.md`](./UPGRADE_V23.md)

---

## 🛠️ Templates & Examples

### 4. **config/TEMPLATE_subject_topics.yaml**
**Configuration Template**

Complete template with:
- Detailed comments for every section
- Examples for all configuration options
- Guidelines for keyword weights
- Difficulty criteria templates

**Use when:** Creating a new subject configuration

**Link:** [`config/TEMPLATE_subject_topics.yaml`](./config/TEMPLATE_subject_topics.yaml)

---

### 5. **config/physics_topics.yaml**
**Reference Implementation**

Working Physics configuration showing:
- 8 well-defined topics
- 150+ weighted keywords
- Formula recognition patterns
- Negative keyword filtering
- Proven to work on 490 pages

**Use when:** You need an example of a production-ready configuration

**Link:** [`config/physics_topics.yaml`](./config/physics_topics.yaml)

---

## 🔧 Scripts & Tools

### Classification Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `scripts/hybrid_classifier_v23.py` | ⭐ v2.3 core engine (Groq Llama 3.3 70B) | Latest, most accurate |
| `scripts/run_hybrid_classification_v23.py` | ⭐ Run v2.3 classification | Classify all Physics pages (v2.3) |
| `scripts/hybrid_classifier.py` | v2.2 core engine (Gemini + Groq) | Fallback if v2.3 has issues |
| `scripts/run_hybrid_classification.py` | Run v2.2 classification | Legacy support |
| `scripts/reclassify_difficulty.py` | Improve difficulty distribution | Fix difficulty imbalance |
| `scripts/analyze_classifications.py` | Check quality metrics | Validate results |

### How to Use Scripts

```bash
# ⭐ RECOMMENDED: Use v2.3 (latest)
python scripts/run_hybrid_classification_v23.py

# Legacy v2.2
python scripts/run_hybrid_classification.py

# Check quality
python scripts/analyze_classifications.py

# Improve difficulty
python scripts/reclassify_difficulty.py
```

---

## 🎯 Quick Reference

### File Structure

```
grademax/
├── config/
│   ├── TEMPLATE_subject_topics.yaml    # Template to copy
│   ├── physics_topics.yaml             # Physics config (reference)
│   └── {subject}_topics.yaml           # Your subject configs
│
├── scripts/
│   ├── hybrid_classifier.py            # Core engine
│   ├── physics_classifier.py           # Physics-specific
│   ├── run_hybrid_classification.py    # Runner
│   ├── analyze_classifications.py      # Quality checker
│   └── {subject}_*.py                  # Your subject scripts
│
├── CLASSIFICATION_RULEBOOK.md          # Complete spec
├── QUICK_START_NEW_SUBJECT.md          # Implementation guide
├── CLASSIFICATION_UPGRADE.md           # What changed in v2.2
└── DOCUMENTATION_INDEX.md              # This file
```

---

## 🚀 Common Tasks

### Task 1: Add a New Subject

1. Read [`QUICK_START_NEW_SUBJECT.md`](./QUICK_START_NEW_SUBJECT.md)
2. Copy `config/TEMPLATE_subject_topics.yaml` → `config/{subject}_topics.yaml`
3. Fill in subject metadata and topics
4. Add keywords (5-10 core, 3-5 support per topic)
5. Create classifier, runner, and analysis scripts
6. Test and validate

**Time:** ~1 hour

---

### Task 2: Improve Classification Quality

**Problem:** Classifications are inaccurate

**Solution:**
1. Run analysis: `python scripts/analyze_{subject}_classifications.py`
2. Identify issues (topic imbalance, low confidence, etc.)
3. Update keywords in `config/{subject}_topics.yaml`:
   - Add more specific core keywords (weight 5)
   - Add formulas and technical terms
   - Add negative keywords for false positives
4. Re-run classification
5. Validate improvements

**Reference:** See "Troubleshooting" section in [CLASSIFICATION_RULEBOOK.md](./CLASSIFICATION_RULEBOOK.md)

---

### Task 3: Fix Difficulty Distribution

**Problem:** 90%+ questions marked as "medium"

**Solution:**
1. Copy `scripts/reclassify_difficulty.py`
2. Update SUBJECT_ID
3. Run: `python scripts/reclassify_{subject}_difficulty.py`
4. Script will re-assess all difficulties with improved prompts
5. Target: 20% easy, 60% medium, 20% hard

**Time:** ~15 minutes

---

### Task 4: Validate Classification Quality

**Problem:** Want to ensure quality meets standards

**Solution:**
1. Run analysis script
2. Check metrics:
   - Coverage: 100% pages have topics ✅
   - Confidence: >70% pages have ≥0.70 confidence ✅
   - Difficulty: 20/60/20 split (±10%) ✅
   - Balance: Topic ratio <3:1 ✅

**Reference:** See "Quality Standards" in [CLASSIFICATION_RULEBOOK.md](./CLASSIFICATION_RULEBOOK.md)

---

## 📊 Current Status

### Physics (Production Ready ✅)

```
Total pages: 490
Coverage: 100%
Topics: 8 (Forces, Electricity, Waves, Energy, Matter, Magnetism, Nuclear, Astrophysics)
Keywords: 150+ (formulas, phrases, technical terms)
Quality: High (most classifications 0.70+ confidence)
```

**Files:**
- Config: `config/physics_topics.yaml`
- Classifier: `scripts/hybrid_classifier.py`
- Runner: `scripts/run_hybrid_classification.py`
- Analysis: `scripts/analyze_classifications.py`

---

## 🎓 Learning Path

### If You're New to the System

1. **Start here:** Read [CLASSIFICATION_UPGRADE.md](./CLASSIFICATION_UPGRADE.md)
   - Understand what we built and why
   - See performance improvements
   
2. **Then read:** [CLASSIFICATION_RULEBOOK.md](./CLASSIFICATION_RULEBOOK.md)
   - Learn the architecture
   - Understand the classification pipeline
   - Study quality standards
   
3. **Try it yourself:** Follow [QUICK_START_NEW_SUBJECT.md](./QUICK_START_NEW_SUBJECT.md)
   - Add a test subject
   - Run classification
   - Validate results

**Time commitment:** 2-3 hours to fully understand the system

---

### If You're Adding Your First Subject

1. **Quick-start guide:** [QUICK_START_NEW_SUBJECT.md](./QUICK_START_NEW_SUBJECT.md)
2. **Template:** `config/TEMPLATE_subject_topics.yaml`
3. **Reference:** `config/physics_topics.yaml`
4. **Validation:** See "Quality Standards" in rulebook

**Time commitment:** 1 hour to add and test new subject

---

### If You're Debugging/Improving

1. **Run analysis:** `python scripts/analyze_{subject}_classifications.py`
2. **Check logs:** Look for low confidence classifications
3. **Review keywords:** See what's matching/not matching
4. **Consult rulebook:** See "Common Pitfalls & Solutions"
5. **Adjust config:** Update keywords and weights
6. **Re-test:** Run on sample questions

**Time commitment:** 15-30 minutes per iteration

---

## 🔍 Key Concepts

### Multi-Pass Classification

**Pass 1: Gemini 2.0 Flash (Bulk)**
- Fast (20 questions/batch, 1500 RPM)
- Good accuracy (0.80+ confidence)
- Low cost (free tier)

**Pass 2: Groq Llama (Refinement)**
- Refines low confidence (<0.70)
- High accuracy (0.90+ confidence)
- Slower (30 RPM)

**Pass 3: Enhanced Keywords (Fallback)**
- Formula recognition
- Weighted scoring
- Negative filtering
- Confidence: 0.30-0.50

**Result:** Best of all approaches, 3x faster than single-pass

---

### Keyword Weighting

| Weight | Meaning | Example |
|--------|---------|---------|
| 5 | Unique formula/phrase | "v=fλ", "half-life" |
| 4 | Very specific term | "electromagnetic induction" |
| 3 | Moderately specific | "acceleration", "circuit" |
| 2 | General term | "energy", "force" |

**Rule:** Use weight 5 for anything that ONLY appears in one topic

---

### Confidence Levels

| Range | Interpretation | Action |
|-------|---------------|--------|
| 0.80-1.00 | High confidence (LLM) | Accept |
| 0.60-0.79 | Medium confidence | Review if critical |
| 0.40-0.59 | Low confidence (keywords) | May need refinement |
| 0.00-0.39 | Very low/no match | Needs manual review |

---

## 📞 Support

### Common Questions

**Q: How do I add a new subject?**  
A: Follow [`QUICK_START_NEW_SUBJECT.md`](./QUICK_START_NEW_SUBJECT.md) - takes ~1 hour

**Q: My classifications are inaccurate. How do I fix them?**  
A: Add more specific core keywords (weight 5), include formulas, add negative keywords. See "Troubleshooting" in rulebook.

**Q: All my questions are marked "medium" difficulty. Why?**  
A: Run `reclassify_difficulty.py` script with improved prompts. See Task 3 above.

**Q: Can I have multiple topics per question?**  
A: Yes, set `allow_multi_tag: true` in config. Not currently implemented but architecture supports it.

**Q: How do I test changes without affecting production?**  
A: Create a test subject in Supabase, classify a subset of pages, validate before deploying to production subject.

---

## 🎉 Summary

You now have:
- ✅ **Complete rulebook** for the classification system
- ✅ **Template** for adding new subjects  
- ✅ **Quick-start guide** with step-by-step instructions
- ✅ **Reference implementation** (Physics with 490 pages)
- ✅ **Quality standards** and validation procedures
- ✅ **Troubleshooting guide** for common issues

**The system is production-ready and battle-tested on Physics.** Adding new subjects follows a standardized process that takes ~1 hour per subject.

---

**Last Updated:** October 24, 2025  
**Version:** 2.3  
**Status:** Production Ready ✅  
**Subjects:** Physics (479 pages, ready for v2.3 classification)

---

## 🆕 What's New in v2.3

**Major Improvements:**
- ✅ **Replaced Gemini with Groq Llama 3.1 70B** (no rate limits!)
- ✅ **4000 char context** (up from 2000) for better accuracy
- ✅ **Page context extraction** for incomplete questions
- ✅ **Disambiguation rules** applied after classification
- ✅ **Better keyword matching** with v2.3 config

**New Files:**
- `scripts/hybrid_classifier_v23.py` - Enhanced classifier
- `scripts/run_hybrid_classification_v23.py` - v2.3 runner

**Usage:**
```bash
python scripts/run_hybrid_classification_v23.py
```
