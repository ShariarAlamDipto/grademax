#!/usr/bin/env python3
"""
LLM Integration Module for GradeMax
Replaces all Gemini calls with LM Studio, keeps OpenAI/Anthropic optional
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from lmstudio_client import get_client


class LLMIntegration:
    """
    Main integration class that replaces Gemini calls
    throughout the GradeMax codebase
    """
    
    def __init__(self):
        """Initialize with LM Studio as primary provider"""
        self.client = get_client()
        self.provider = "lmstudio"  # Primary provider
        
        # Check for removed providers
        if 'GEMINI_API_KEY' in os.environ:
            raise RuntimeError(
                "❌ GEMINI_API_KEY found in environment!\n"
                "Gemini is no longer supported. Please remove this key.\n"
                "The system now uses LM Studio for offline inference."
            )
    
    def classify_question(
        self,
        question_text: str,
        subject: str,
        paper_type: Optional[str] = None,
        topics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Classify a question and extract topics/metadata
        
        This replaces all previous classify_with_gemini() calls
        
        Args:
            question_text: The exam question text
            subject: Subject name (e.g., "Physics", "Mathematics")
            paper_type: Optional paper type (e.g., "Paper 1", "Paper 4")
            topics: Optional list of known topics
        
        Returns:
            Classification dict with topics, subtopics, difficulty
        """
        return self.client.classify_question(
            question_text=question_text,
            subject=subject,
            topics=topics
        )
    
    def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        This replaces all previous Gemini embedding calls
        
        Args:
            texts: List of texts to embed
            batch_size: Process in batches (not used for local inference)
        
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for i, text in enumerate(texts):
            if i % 10 == 0:
                print(f"Embedding {i}/{len(texts)}...")
            embedding = self.client.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate single embedding
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector
        """
        return self.client.generate_embedding(text)
    
    def extract_topics_from_question(
        self,
        question_text: str,
        subject: str,
        known_topics: Optional[List[str]] = None
    ) -> List[str]:
        """
        Extract topic tags from a question
        
        Args:
            question_text: Question text
            subject: Subject name
            known_topics: Optional list of valid topics
        
        Returns:
            List of topic names
        """
        result = self.classify_question(
            question_text=question_text,
            subject=subject,
            topics=known_topics
        )
        return result.get('topics', [])
    
    def tag_question_with_metadata(
        self,
        question_text: str,
        subject: str,
        year: Optional[int] = None,
        paper_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Full question tagging with all metadata
        
        Replaces the complete Gemini-based tagging pipeline
        
        Args:
            question_text: Question text
            subject: Subject name
            year: Exam year
            paper_code: Paper code (e.g., "9231/41")
        
        Returns:
            Complete metadata dict
        """
        classification = self.classify_question(
            question_text=question_text,
            subject=subject
        )
        
        return {
            'question_text': question_text,
            'subject': subject,
            'year': year,
            'paper_code': paper_code,
            'topics': classification.get('topics', []),
            'subtopics': classification.get('subtopics', []),
            'difficulty': classification.get('difficulty', 'medium'),
            'reasoning': classification.get('reasoning', ''),
            'embedding': self.generate_embedding(question_text)
        }
    
    def validate_topic_assignment(
        self,
        question_text: str,
        assigned_topic: str,
        subject: str
    ) -> Dict[str, Any]:
        """
        Validate if a topic assignment is correct
        
        Args:
            question_text: Question text
            assigned_topic: Currently assigned topic
            subject: Subject name
        
        Returns:
            Validation result with confidence score
        """
        classification = self.classify_question(
            question_text=question_text,
            subject=subject
        )
        
        predicted_topics = classification.get('topics', [])
        is_valid = assigned_topic in predicted_topics
        
        return {
            'is_valid': is_valid,
            'assigned_topic': assigned_topic,
            'predicted_topics': predicted_topics,
            'confidence': 'high' if is_valid else 'low',
            'suggestion': predicted_topics[0] if predicted_topics else None
        }
    
    def reason_about_question(
        self,
        question_text: str,
        context: str,
        subject: str
    ) -> str:
        """
        General reasoning about a question
        
        Args:
            question_text: The question
            context: Additional context
            subject: Subject name
        
        Returns:
            Reasoning text
        """
        prompt = f"""Context: {context}

Question: {question_text}

Please provide a detailed reasoning about this question."""
        
        return self.client.reason(
            prompt=prompt,
            subject=subject
        )


# ============================================================================
# Migration Helper Functions
# ============================================================================

def migrate_from_gemini():
    """
    Check for Gemini usage and provide migration guidance
    """
    print("\n" + "="*70)
    print("🔄 GEMINI → LM STUDIO MIGRATION CHECK")
    print("="*70)
    
    # Check environment
    gemini_key = os.getenv('GEMINI_API_KEY')
    if gemini_key:
        print("\n❌ Found GEMINI_API_KEY in environment")
        print("   Remove it with: unset GEMINI_API_KEY (Unix) or $env:GEMINI_API_KEY='' (Windows)")
    else:
        print("\n✅ No GEMINI_API_KEY found")
    
    # Check for Gemini imports in codebase
    codebase_root = Path(__file__).parent.parent.parent
    python_files = list(codebase_root.rglob("*.py"))
    
    gemini_references = []
    for py_file in python_files:
        try:
            content = py_file.read_text(encoding='utf-8')
            if 'google.generativeai' in content or 'import genai' in content:
                gemini_references.append(py_file)
        except Exception:
            pass
    
    if gemini_references:
        print(f"\n⚠️ Found {len(gemini_references)} files with Gemini imports:")
        for ref in gemini_references[:5]:  # Show first 5
            print(f"   - {ref.relative_to(codebase_root)}")
        print("\n   Replace with:")
        print("   from grademax_llm_hybrid.scripts.integrate_llm import LLMIntegration")
    else:
        print("\n✅ No Gemini imports found in codebase")
    
    print("\n" + "="*70)


# ============================================================================
# Singleton Instance
# ============================================================================

_integration = None

def get_llm() -> LLMIntegration:
    """Get or create LLM integration singleton"""
    global _integration
    if _integration is None:
        _integration = LLMIntegration()
    return _integration


if __name__ == "__main__":
    # Run migration check
    migrate_from_gemini()
    
    # Test integration
    print("\n🧪 Testing LM Studio integration...")
    llm = get_llm()
    
    test_question = "A block of mass 5 kg is placed on a horizontal surface. Calculate the normal reaction force."
    result = llm.classify_question(
        question_text=test_question,
        subject="Physics"
    )
    
    print(f"\n✅ Classification successful:")
    print(f"   Topics: {result.get('topics', [])}")
    print(f"   Difficulty: {result.get('difficulty', 'unknown')}")
