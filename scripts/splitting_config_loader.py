#!/usr/bin/env python3
"""
Subject-specific document splitting configuration loader
Loads YAML configurations for different subjects to customize question detection
"""

import yaml
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class QuestionPattern:
    """A single pattern for detecting question numbers"""
    regex: str
    description: str
    validation: Optional[Dict] = None


@dataclass
class SplittingConfig:
    """Configuration for splitting a specific subject's papers"""
    subject_code: str
    subject_name: str
    question_patterns: Dict[str, List[QuestionPattern]]
    markscheme_patterns: Dict
    skip_patterns: List[str]
    validation: Dict
    multi_page: Dict
    format_detection: Optional[Dict] = None
    page_number_detection: Optional[Dict] = None
    continuation_markers: Optional[List[str]] = None


class SplittingConfigLoader:
    """Loads and manages subject-specific splitting configurations"""
    
    def __init__(self, config_path: str = "config/document_splitting_config.yaml"):
        self.config_path = Path(config_path)
        self.configs: Dict[str, SplittingConfig] = {}
        self._load_configs()
    
    def _load_configs(self):
        """Load all configurations from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Parse each subject config (skip template and metadata)
        for subject_key, config_data in data.items():
            if subject_key.startswith('_'):
                continue  # Skip template and private keys
            
            # Parse question patterns
            question_patterns = {}
            if 'question_patterns' in config_data:
                for priority, patterns in config_data['question_patterns'].items():
                    if isinstance(patterns, list):
                        question_patterns[priority] = [
                            QuestionPattern(
                                regex=p['regex'],
                                description=p['description'],
                                validation=p.get('validation')
                            )
                            for p in patterns
                        ]
            
            # Create config object
            self.configs[subject_key] = SplittingConfig(
                subject_code=config_data.get('subject_code', ''),
                subject_name=config_data.get('subject_name', ''),
                question_patterns=question_patterns,
                markscheme_patterns=config_data.get('markscheme_patterns', {}),
                skip_patterns=config_data.get('skip_patterns', []),
                validation=config_data.get('validation', {}),
                multi_page=config_data.get('multi_page', {}),
                format_detection=config_data.get('format_detection'),
                page_number_detection=config_data.get('page_number_detection'),
                continuation_markers=config_data.get('continuation_markers')
            )
    
    def get_config(self, subject_name: str) -> Optional[SplittingConfig]:
        """
        Get configuration for a subject
        
        Args:
            subject_name: Subject name (e.g., "Further Pure Maths", "Physics")
        
        Returns:
            SplittingConfig object or None if not found
        """
        # Normalize subject name to config key
        # "Further Pure Maths" -> "further_pure_maths"
        key = subject_name.lower().replace(' ', '_').replace('-', '_')
        
        return self.configs.get(key)
    
    def get_config_by_code(self, subject_code: str) -> Optional[SplittingConfig]:
        """
        Get configuration by subject code (e.g., "4PM1", "4PH1")
        
        Args:
            subject_code: Subject code
        
        Returns:
            SplittingConfig object or None if not found
        """
        for config in self.configs.values():
            if config.subject_code == subject_code:
                return config
        return None
    
    def list_subjects(self) -> List[str]:
        """List all configured subjects"""
        return [config.subject_name for config in self.configs.values()]


class ConfigurableQuestionDetector:
    """Question detector that uses subject-specific configurations"""
    
    def __init__(self, config: SplittingConfig):
        self.config = config
    
    def detect_question_start(self, text: str, is_markscheme: bool = False, 
                            year: Optional[int] = None) -> Optional[str]:
        """
        Detect if page starts with a question number using configured patterns
        
        Args:
            text: Page text to analyze
            is_markscheme: Whether this is a markscheme (different patterns)
            year: Paper year (for format-specific detection)
        
        Returns:
            Question number string or None
        """
        if is_markscheme:
            return self._detect_markscheme(text)
        else:
            return self._detect_question_paper(text, year)
    
    def _detect_markscheme(self, text: str) -> Optional[str]:
        """Detect question number in markscheme using configured patterns"""
        ms_config = self.config.markscheme_patterns
        
        if 'table_format' in ms_config:
            table_config = ms_config['table_format']
            marker = table_config['marker'].lower()
            pattern = table_config['pattern']
            search_range = table_config.get('search_after_marker', 5)
            
            lines = text[:1000].split('\n')
            
            for i, line in enumerate(lines):
                if marker in line.strip().lower() and len(line.strip()) < 10:
                    # Found marker, search next N lines
                    for j in range(i+1, min(i+1+search_range, len(lines))):
                        match = re.match(pattern, lines[j].strip())
                        if match:
                            q_num = match.group(1)
                            try:
                                num = int(q_num)
                                min_q = self.config.validation.get('min_question', 1)
                                max_q = self.config.validation.get('max_question', 20)
                                if min_q <= num <= max_q:
                                    return q_num
                            except ValueError:
                                pass
                    break
        
        return None
    
    def _detect_question_paper(self, text: str, year: Optional[int] = None) -> Optional[str]:
        """Detect question number in question paper using configured patterns"""
        lines = text.strip().split('\n')
        
        # Skip if matches skip patterns (only check first 200 chars - skip patterns indicate non-content pages)
        text_first_200 = text.lower()[:200]
        for skip_pattern in self.config.skip_patterns:
            if skip_pattern.lower() in text_first_200:
                return None
        
        # Determine start line based on format (old vs new)
        start_line = 0
        if self.config.format_detection and year:
            old_years = self.config.format_detection.get('old_format', {}).get('years', [])
            new_years = self.config.format_detection.get('new_format', {}).get('years', [])
            
            if year in old_years:
                start_line = self.config.format_detection['old_format'].get('start_line', 0)
            elif year in new_years:
                start_line = self.config.format_detection['new_format'].get('start_line', 5)
        
        # Check for page numbers (if configured)
        if self.config.page_number_detection:
            pg_config = self.config.page_number_detection
            filter_pattern = pg_config.get('filter_pattern', '')
            check_next = pg_config.get('check_next_line', False)
            check_first_n = pg_config.get('apply_to_first_n_lines', 3)
        else:
            filter_pattern = None
            check_next = False
            check_first_n = 0
        
        # Priority 1: Most reliable patterns (return immediately)
        if 'priority_1' in self.config.question_patterns:
            for pattern_config in self.config.question_patterns['priority_1']:
                for i in range(start_line, min(start_line + 30, len(lines))):
                    line = lines[i].strip()
                    
                    if not line:
                        continue
                    
                    match = re.match(pattern_config.regex, line)
                    if match:
                        q_num = match.group(1)
                        if self._validate_question_number(q_num):
                            return q_num
        
        # Priority 2: Standalone numbers with validation
        best_match = None
        best_match_line = 999
        
        if 'priority_2' in self.config.question_patterns:
            for pattern_config in self.config.question_patterns['priority_2']:
                for i in range(start_line, min(start_line + 30, len(lines))):
                    line = lines[i].strip()
                    
                    if not line:
                        continue
                    
                    # Skip page numbers (if in first N lines and followed by filter pattern)
                    if filter_pattern and i < check_first_n:
                        if check_next and i+1 < len(lines):
                            if re.search(filter_pattern, lines[i+1]):
                                continue
                    
                    match = re.match(pattern_config.regex, line)
                    if match:
                        q_num = match.group(1)
                        
                        if not self._validate_question_number(q_num):
                            continue
                        
                        # Check for validation keywords
                        if pattern_config.validation:
                            keywords = pattern_config.validation.get('keywords', [])
                            search_range = pattern_config.validation.get('search_range', 15)
                            
                            has_keywords = False
                            for j in range(i+1, min(i+1+search_range, len(lines))):
                                next_line = lines[j].strip().lower()
                                if any(kw.lower() in next_line for kw in keywords):
                                    has_keywords = True
                                    break
                            
                            if has_keywords and i < best_match_line:
                                best_match = q_num
                                best_match_line = i
        
        return best_match
    
    def _validate_question_number(self, q_num: str) -> bool:
        """Validate question number is in expected range"""
        try:
            num = int(q_num)
            min_q = self.config.validation.get('min_question', 1)
            max_q = self.config.validation.get('max_question', 20)
            return min_q <= num <= max_q
        except ValueError:
            return False
    
    def is_continuation_page(self, text: str) -> bool:
        """Check if page is a continuation page"""
        if not self.config.continuation_markers:
            return False
        
        text_lower = text.lower()
        for marker in self.config.continuation_markers:
            if marker.lower() in text_lower and "question" in text_lower:
                return True
        return False


# Convenience function
def load_detector_for_subject(subject_name: str, 
                              config_path: str = "config/document_splitting_config.yaml") -> Optional[ConfigurableQuestionDetector]:
    """
    Load a detector for a specific subject
    
    Args:
        subject_name: Subject name (e.g., "Further Pure Maths")
        config_path: Path to config file
    
    Returns:
        ConfigurableQuestionDetector or None if subject not found
    """
    loader = SplittingConfigLoader(config_path)
    config = loader.get_config(subject_name)
    
    if config:
        return ConfigurableQuestionDetector(config)
    return None


# Example usage
if __name__ == "__main__":
    # Load configuration
    loader = SplittingConfigLoader()
    
    print("Available subjects:")
    for subject in loader.list_subjects():
        print(f"  - {subject}")
    
    # Get Further Pure Maths config
    config = loader.get_config("Further Pure Maths")
    if config:
        print(f"\nConfiguration for {config.subject_name}:")
        print(f"  Code: {config.subject_code}")
        print(f"  Question patterns: {len(config.question_patterns)} priorities")
        print(f"  Expected questions: {config.validation.get('expected_range')}")
        print(f"  Multi-page enabled: {config.multi_page.get('enabled')}")
        
        # Create detector
        detector = ConfigurableQuestionDetector(config)
        print(f"\n✅ Detector created for {config.subject_name}")
