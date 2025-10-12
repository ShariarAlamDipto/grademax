# 🎯 Classification System Improvements

## Overview
Enhanced the Gemini-based topic classification with **textbook-aware prompting** and **keyword-based guardrails** to improve accuracy for IGCSE Physics questions.

---

## 🧩 Step 1 – Textbook Structure Integration

The classification system now embeds the complete IGCSE Physics topic hierarchy based on the **Edexcel 2017 specification**:

### Topic Structure

| Code | Topic | Key Concepts |
|------|-------|--------------|
| **1** | **Forces and Motion** | speed, velocity, acceleration, force = ma, momentum, terminal velocity, motion graphs |
| **2** | **Electricity** | current, voltage, resistance, Ohm's law, series/parallel circuits, power, energy = VIt |
| **3** | **Waves** | reflection, refraction, diffraction, sound, electromagnetic spectrum, wave equation v = fλ |
| **4** | **Energy Transfers** | kinetic/potential energy, efficiency, conduction/convection/radiation, insulation |
| **5** | **Solids/Liquids/Gases** | density, pressure = F/A, gas laws (pV = k), temperature, molecular motion |
| **6** | **Magnetism & Electromagnetism** | magnetic fields, induced currents, motors, transformers, flux |
| **7** | **Radioactivity & Particles** | alpha/beta/gamma decay, half-life, fission vs fusion, radiation hazards |
| **8** | **Astrophysics** | solar system, orbits, red shift, universe expansion, gravitational forces |

---

## 🧠 Step 2 – Enhanced Gemini Prompt

The new prompt gives Gemini **"textbook-level awareness"** of what belongs to each topic:

```python
prompt = f"""You are classifying IGCSE Physics exam questions by topic.
Below are all valid topic codes and their detailed descriptors based on the Edexcel 2017 specification:

1. Forces and Motion – motion graphs, speed, velocity, acceleration, force = ma, momentum...
2. Electricity – current, voltage, potential difference, resistance, Ohm's law...
3. Waves – sound, light, reflection, refraction, diffraction, EM spectrum...
4. Energy Transfers – kinetic/potential energy, efficiency, heat transfer...
5. Solids/Liquids/Gases – density, pressure = F/A, gas laws, temperature...
6. Magnetism and Electromagnetism – fields, motors, induction, transformers...
7. Radioactivity and Particles – decay, half-life, radiation, nuclear energy...
8. Astrophysics – orbits, gravity, red shift, universe expansion...

INSTRUCTIONS:
• Identify which topic best matches this question (return ONE primary topic).
• Base your choice strictly on the physics concepts being tested.
• Consider the equations, units, and physical principles mentioned.
• If sub-questions test different topics, choose the DOMINANT one.
"""
```

### Key Improvements:
- ✅ **Explicit topic descriptors** with physics concepts and equations
- ✅ **Clear instructions** to focus on concepts, not just vocabulary
- ✅ **Dominant topic rule** for multi-part questions
- ✅ **Longer context** (2500 chars vs 2000)

---

## 🛡️ Step 3 – Keyword-Based Guardrails

A **lightweight rule-based layer** reinforces low-confidence predictions:

### Keyword Map

```python
KEYWORD_MAP = {
    # Topic 1: Forces and Motion
    "force": "1", "momentum": "1", "acceleration": "1", "velocity": "1", "speed": "1",
    "mass": "1", "weight": "1", "terminal velocity": "1", "newton": "1",
    
    # Topic 2: Electricity
    "current": "2", "ohm": "2", "circuit": "2", "voltage": "2", "resistance": "2",
    "potential difference": "2", "series": "2", "parallel": "2", "power": "2",
    
    # Topic 3: Waves
    "wave": "3", "reflection": "3", "frequency": "3", "refraction": "3", 
    "diffraction": "3", "electromagnetic": "3", "spectrum": "3", "sound": "3",
    
    # Topic 4: Energy
    "energy": "4", "efficiency": "4", "conduction": "4", "convection": "4",
    "kinetic": "4", "potential energy": "4", "insulation": "4", "thermal": "4",
    
    # Topic 5: Solids/Liquids/Gases
    "pressure": "5", "density": "5", "temperature": "5", "gas law": "5",
    "solid": "5", "liquid": "5", "molecule": "5", "volume": "5",
    
    # Topic 6: Magnetism
    "magnet": "6", "induced": "6", "coil": "6", "motor": "6", "transformer": "6",
    "generator": "6", "flux": "6",
    
    # Topic 7: Radioactivity
    "alpha": "7", "beta": "7", "gamma": "7", "half-life": "7", "radioactive": "7",
    "nuclear": "7", "fission": "7", "fusion": "7", "decay": "7",
    
    # Topic 8: Astrophysics
    "orbit": "8", "planet": "8", "red shift": "8", "universe": "8", "solar": "8",
    "gravity": "8", "satellite": "8", "star": "8"
}
```

### How It Works:

1. **Primary Classification**: Gemini analyzes the question and returns a topic with confidence score
2. **Low-Confidence Check**: If `confidence < 0.7`, keyword checker activates
3. **Keyword Scoring**: Count keyword matches for each topic
4. **Validation**: Log discrepancies between Gemini and keyword suggestions
5. **Fallback**: If Gemini fails, use keyword-based classification

```python
# Apply keyword-based guardrail if confidence is low
if classification.confidence < 0.7:
    keyword_topic = self._keyword_check(page_text.lower())
    if keyword_topic and keyword_topic != classification.topic:
        print(f"⚠️ Low confidence ({classification.confidence:.2f}), "
              f"keyword suggests topic {keyword_topic}")
```

---

## 📊 Expected Improvements

### Before:
- ❌ Generic prompt without domain knowledge
- ❌ No fallback mechanism for errors
- ❌ Inconsistent handling of multi-topic questions
- ❌ Short context window (2000 chars)

### After:
- ✅ **Textbook-aligned** topic descriptors with equations/concepts
- ✅ **Keyword guardrails** for low-confidence predictions
- ✅ **Clear dominant topic rule** for multi-part questions
- ✅ **Longer context** (2500 chars) for better understanding
- ✅ **Robust error handling** with keyword fallback
- ✅ **Confidence logging** for quality monitoring

---

## 🔍 Classification Process Flow

```
┌─────────────────────────────────────┐
│  Extract Question Text (2500 chars) │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Gemini Analysis with Enhanced      │
│  Textbook-Aware Prompt              │
│  - Topic descriptors                │
│  - Physics concepts                 │
│  - Equations & units                │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Classification Result              │
│  - topic: "1"                       │
│  - difficulty: "medium"             │
│  - confidence: 0.85                 │
└──────────────┬──────────────────────┘
               │
               ▼
       ┌───────┴────────┐
       │ confidence < 0.7? │
       └───────┬────────┘
               │
       ┌───────┴────────┐
       │ YES            │ NO
       ▼                ▼
┌──────────────┐  ┌────────────┐
│ Keyword      │  │ Accept     │
│ Validation   │  │ Gemini     │
│ Check        │  │ Result     │
└──────┬───────┘  └────────────┘
       │
       ▼
┌──────────────────┐
│ Log Discrepancy  │
│ if topics differ │
└──────────────────┘
```

---

## 🚀 Usage

The improved classifier is **already integrated** into `page_based_ingest.py`. No changes needed to your workflow:

```bash
# Process papers as before
python scripts/page_based_ingest.py "data/raw/.../QP.pdf" "data/raw/.../MS.pdf"
```

### Example Output:

```
4️⃣ Classifying and uploading pages...
   ✅ [1/11] Q1: Topic 1 (Forces) | medium | conf: 0.92
   ✅ [2/11] Q2: Topic 2 (Electricity) | easy | conf: 0.88
   ⚠️  [3/11] Q3: Low confidence (0.65), keyword suggests topic 3
   ✅ [3/11] Q3: Topic 3 (Waves) | hard | conf: 0.65
   ...
```

---

## 📈 Monitoring Classification Quality

### Check Confidence Scores:
- **High (≥0.8)**: Gemini is very confident, likely correct
- **Medium (0.6-0.79)**: Good classification, keyword check activated
- **Low (<0.6)**: Uncertain, review manually if needed

### Look for Keyword Warnings:
```
⚠️ Low confidence (0.65), keyword suggests topic 3
```
This indicates the keyword checker found evidence for a different topic. Review these cases to improve the system.

---

## 🔧 Future Enhancements

1. **Multi-Topic Support**: Extend schema to allow multiple topics per question
2. **Sub-Topic Granularity**: Classify into specific sub-topics (e.g., 1.1, 1.2)
3. **Learning from Corrections**: Track manual corrections to improve keywords
4. **Equation Extraction**: Parse LaTeX/equations for better topic matching
5. **Historical Data**: Use past exam statistics to weight topic probabilities

---

## 📝 Technical Details

**File**: `scripts/single_topic_classifier.py`

**Changes:**
1. Added `KEYWORD_MAP` class variable with 50+ physics terms
2. Enhanced prompt with textbook-aligned topic descriptors
3. Implemented `_keyword_check()` method for fallback classification
4. Increased context window from 2000 → 2500 characters
5. Added low-confidence guardrail logic

**Dependencies**: No new dependencies required

**Performance**: Same 15 RPM rate limit (4-second delay between calls)

---

## ✅ Testing Recommendations

After processing papers, verify classification quality:

1. **Check Database**:
   ```sql
   SELECT topics, COUNT(*) 
   FROM pages 
   WHERE is_question = true 
   GROUP BY topics 
   ORDER BY COUNT(*) DESC;
   ```

2. **Review Low-Confidence Cases**:
   Look for `⚠️` warnings in console output

3. **Spot-Check Examples**:
   Review a few questions per topic to ensure accuracy

4. **Compare to Previous System**:
   If you have old data, compare topic distributions

---

## 🎓 Based On

This improvement follows best practices from:
- **Edexcel IGCSE Physics Specification (2017)**
- **Cambridge IGCSE Physics Textbook** topic structure
- **Gemini prompt engineering** for domain-specific classification
- **Hybrid AI + rule-based systems** for robustness

---

## 📞 Support

If you encounter misclassifications:
1. Note the question number and expected topic
2. Check console for confidence scores
3. Review the keyword matches
4. Consider adding more keywords to `KEYWORD_MAP`

The system will improve over time as you process more papers and refine the keyword map!
