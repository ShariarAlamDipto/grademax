# 📝 Subject-Specific Document Splitting Configuration

## Overview

GradeMax now supports **subject-specific document splitting configurations**. Each subject can have its own rules for detecting question numbers, handling different PDF formats, and linking markschemes.

This allows:
- ✅ Different question detection patterns per subject
- ✅ Support for old/new paper formats (e.g., 2011-2015 vs 2016+)
- ✅ Easy addition of new subjects via YAML config
- ✅ Subject-specific validation rules

## Files

```
config/
  └── document_splitting_config.yaml    # All splitting configurations

classification/
  └── further_pure_maths_topics.yaml    # FPM classification rules

scripts/
  ├── splitting_config_loader.py        # Config loader module
  ├── reprocess_all_papers_configurable.py  # Configurable processor
  └── reprocess_all_papers.py           # Original (Physics-specific)
```

## Quick Start

### Processing Papers with Configurations

```bash
# Process all subjects using their configs
python scripts\reprocess_all_papers_configurable.py --yes

# Interactive mode
python scripts\reprocess_all_papers_configurable.py
```

### Adding a New Subject

**1. Add configuration to `config/document_splitting_config.yaml`:**

```yaml
chemistry:
  subject_code: "4CH1"
  subject_name: "Chemistry"
  
  question_patterns:
    priority_1:
      - regex: '^\s*(\d+)\s+[A-Z(]'
        description: "Number + space + uppercase"
    
    priority_2:
      - regex: '^\s*(\d+)\s*$'
        description: "Standalone number"
        validation:
          keywords: ["reaction", "equation", "compound"]
          search_range: 15
  
  validation:
    min_question: 1
    max_question: 15
    expected_range: [10, 15]
  
  multi_page:
    enabled: true
    group_by_number: true
```

**2. Update subject mapping in `reprocess_all_papers_configurable.py`:**

```python
subject_mapping = {
    "Further Pure Mathematics": "Further Pure Maths",
    "Physics": "Physics",
    "Chemistry": "Chemistry"  # Add this line
}
```

**3. Process papers:**

```bash
python scripts\reprocess_all_papers_configurable.py --yes
```

## Configuration Reference

### Question Detection Patterns

**Priority 1**: Most reliable patterns (returns immediately)
```yaml
priority_1:
  - regex: '^\s*(\d+)\s+[A-Z(]'
    description: "Number + space + uppercase (e.g., '1 Solve')"
```

**Priority 2**: Requires validation (checks for keywords)
```yaml
priority_2:
  - regex: '^\s*(\d+)\s*$'
    description: "Standalone number"
    validation:
      keywords: ["given", "find", "calculate"]
      search_range: 15
```

### Markscheme Detection

```yaml
markscheme_patterns:
  table_format:
    marker: "marks"
    pattern: '^\s*(\d+)\s*[a-z]?'
    search_after_marker: 5
```

### Format-Specific Detection

Handle different formats by year:

```yaml
format_detection:
  old_format:
    years: [2011, 2012, 2013, 2014, 2015]
    start_line: 0  # Check from beginning
  
  new_format:
    years: [2016, 2017, 2018, 2019, 2020, 2021]
    start_line: 5  # Skip headers
```

### Page Number Filtering

Prevent page numbers from being detected as questions:

```yaml
page_number_detection:
  filter_pattern: '\*P\d+'
  check_next_line: true
  apply_to_first_n_lines: 3
```

### Skip Patterns

Pages to ignore during detection:

```yaml
skip_patterns:
  - "formulae"
  - "Turn over"
  - "DO NOT WRITE"
  - "Centre Number"
```

### Validation

```yaml
validation:
  min_question: 1
  max_question: 11
  expected_range: [9, 11]
```

### Multi-Page Handling

```yaml
multi_page:
  enabled: true
  group_by_number: true
  include_blank_pages: true
```

## Current Subjects

### Further Pure Mathematics (4PM1)

**Features:**
- Old format detection (2011-2015)
- New format detection (2016+)
- Page number filtering with `*P...` codes
- Priority-based pattern matching
- Expected 9-11 questions per paper

**Patterns:**
- Priority 1: `"1 Solve"`, `"2 Given"`, `"3 (a)"`
- Priority 2: Standalone `"2"` followed by `"(a) Given"`

**Status:** ✅ Working - 658 questions detected, 79.8% markscheme linking

### Physics (4PH1)

**Features:**
- Standard question detection
- Expected 12-20 questions per paper

**Status:** ✅ Working

## Testing Configuration

```python
from splitting_config_loader import SplittingConfigLoader, ConfigurableQuestionDetector

# Load config
loader = SplittingConfigLoader()
config = loader.get_config("Further Pure Maths")

# Create detector
detector = ConfigurableQuestionDetector(config)

# Test detection
import fitz
doc = fitz.open("path/to/paper.pdf")
for i in range(len(doc)):
    text = doc[i].get_text()
    q_num = detector.detect_question_start(text, year=2011)
    print(f"Page {i+1}: Q{q_num}")
```

## Troubleshooting

### Issue: Wrong question count

**Solution:** Adjust `expected_range` in validation:
```yaml
validation:
  expected_range: [8, 12]  # Wider range
```

### Issue: Missing questions

**Solution:** Add more Priority 2 keywords:
```yaml
validation:
  keywords: ["given", "find", "show", "calculate", "prove"]
```

### Issue: Page numbers detected as questions

**Solution:** Configure page number filtering:
```yaml
page_number_detection:
  filter_pattern: '\*P\d+'
  check_next_line: true
  apply_to_first_n_lines: 3
```

### Issue: Old format not working

**Solution:** Add format detection:
```yaml
format_detection:
  old_format:
    years: [2011, 2012, 2013]
    start_line: 0
```

## Migration Guide

### From Original Script to Configurable

**Before (hardcoded):**
```python
# In reprocess_all_papers.py
detector = QuestionDetector()
questions = detector.detect_questions(pdf_path)
```

**After (configurable):**
```python
# In reprocess_all_papers_configurable.py
config = loader.get_config("Subject Name")
detector = ConfigurableQuestionDetector(config)
questions = detector.detect_questions(pdf_path, year=2020)
```

## Benefits

✅ **Maintainability**: All splitting logic in one YAML file  
✅ **Extensibility**: Add new subjects without code changes  
✅ **Flexibility**: Different rules per subject  
✅ **Testability**: Easy to test configurations  
✅ **Documentation**: Self-documenting YAML format  

## Next Steps

1. **Test with current papers**: `python scripts\reprocess_all_papers_configurable.py --yes`
2. **Add more subjects**: Edit `config/document_splitting_config.yaml`
3. **Fine-tune patterns**: Adjust regex and keywords as needed
4. **Create classification files**: Add YAML files to `classification/` folder

## Support

For issues or questions:
1. Check configuration in `config/document_splitting_config.yaml`
2. Test with `splitting_config_loader.py`
3. Review pattern matching with sample PDFs
4. Adjust validation ranges and keywords

---

**Version**: 2.3  
**Last Updated**: October 2025  
**Status**: ✅ Production Ready
