#!/usr/bin/env python3
"""
Supabase Client for Python - GradeMax Phase 2
Uses Supabase REST API instead of direct PostgreSQL connection
"""

import os
import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime


class SupabaseClient:
    """Simple Supabase client using REST API"""
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """
        Initialize Supabase client
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase service_role key (for server-side operations)
        """
        # Try multiple environment variable names for flexibility
        self.url = supabase_url or os.getenv('SUPABASE_URL') or os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        self.key = supabase_key or os.getenv('SUPABASE_SERVICE_ROLE') or os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
        
        if not self.url or not self.key:
            raise ValueError(
                "Supabase credentials not found. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE "
                "(or NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY) environment variables."
            )
        
        self.rest_url = f"{self.url}/rest/v1"
        self.headers = {
            'apikey': self.key,
            'Authorization': f'Bearer {self.key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
    
    def insert(self, table: str, data: Dict | List[Dict]) -> Dict:
        """
        Insert one or more rows into a table
        
        Args:
            table: Table name
            data: Dict for single row, or List[Dict] for multiple rows
            
        Returns:
            Dict with inserted data
        """
        url = f"{self.rest_url}/{table}"
        
        # Ensure data is a list
        if isinstance(data, dict):
            data = [data]
        
        response = requests.post(url, headers=self.headers, json=data)
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Insert failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    def select(
        self, 
        table: str, 
        columns: str = "*",
        filters: Dict[str, Any] = None,
        limit: int = None
    ) -> List[Dict]:
        """
        Select rows from a table
        
        Args:
            table: Table name
            columns: Columns to select (e.g., "id,name,email")
            filters: Dictionary of filters (e.g., {"year": 2019, "season": "Jun"})
            limit: Maximum number of rows to return
            
        Returns:
            List of rows
        """
        url = f"{self.rest_url}/{table}?select={columns}"
        
        # Add filters
        if filters:
            for key, value in filters.items():
                # Check if value already has operator (eq., neq., gt., etc.)
                if isinstance(value, str) and any(op in value for op in ['eq.', 'neq.', 'gt.', 'gte.', 'lt.', 'lte.', 'like.', 'ilike.', 'is.', 'in.', 'cs.', 'cd.']):
                    # Value already has operator, use as-is
                    url += f"&{key}={value}"
                else:
                    # No operator, add eq.
                    url += f"&{key}=eq.{value}"
        
        # Add limit
        if limit:
            url += f"&limit={limit}"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Select failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    def update(self, table: str, filters: Dict[str, Any], data: Dict) -> Dict:
        """
        Update rows in a table
        
        Args:
            table: Table name
            filters: Dictionary of filters to match rows
            data: Dictionary of columns to update
            
        Returns:
            Dict with updated data
        """
        url = f"{self.rest_url}/{table}?"
        
        # Add filters
        filter_parts = []
        for key, value in filters.items():
            if isinstance(value, str):
                filter_parts.append(f"{key}=eq.{value}")
            else:
                filter_parts.append(f"{key}=eq.{value}")
        url += "&".join(filter_parts)
        
        response = requests.patch(url, headers=self.headers, json=data)
        
        if response.status_code != 200:
            raise Exception(f"Update failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    def rpc(self, function_name: str, params: Dict = None) -> Any:
        """
        Call a PostgreSQL function via RPC
        
        Args:
            function_name: Name of the function
            params: Dictionary of parameters
            
        Returns:
            Function result
        """
        url = f"{self.rest_url}/rpc/{function_name}"
        
        response = requests.post(
            url, 
            headers=self.headers, 
            json=params or {}
        )
        
        if response.status_code != 200:
            raise Exception(f"RPC failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_or_create_paper(
        self,
        subject_code: str,
        year: int,
        season: str,
        paper_number: str,
        qp_url: str = None,
        ms_url: str = None
    ) -> str:
        """
        Get existing paper or create new one
        
        Returns:
            Paper UUID
        """
        # Get subject_id
        subjects = self.select('subjects', 'id', {'code': subject_code}, limit=1)
        if not subjects:
            raise Exception(f"Subject not found: {subject_code}")
        subject_id = subjects[0]['id']
        
        # Check if paper exists
        papers = self.select(
            'papers',
            'id',
            {
                'subject_id': subject_id,
                'year': year,
                'season': season,
                'paper_number': paper_number
            },
            limit=1
        )
        
        if papers:
            return papers[0]['id']
        
        # Create new paper
        paper_data = {
            'subject_id': subject_id,
            'year': year,
            'season': season,
            'paper_number': paper_number,
            'pdf_url': qp_url,
            'markscheme_pdf_url': ms_url
        }
        
        result = self.insert('papers', paper_data)
        return result[0]['id']
    
    def insert_question_with_topics(
        self,
        paper_id: str,
        question_number: str,
        topics: List[Dict],  # List of {topic_code, confidence, subpart_label, method}
        text: str = None,
        marks: int = None,
        difficulty: int = None,
        qp_page_index: int = None,
        qp_page_count: int = 1,
        page_pdf_url: str = None,
        ms_page_indices: List[int] = None,
        ms_pdf_url: str = None,
        text_excerpt: str = None,
        has_diagram: bool = False,
        classification_confidence: float = 0.0,
        subparts: List[Dict] = None
    ) -> str:
        """
        Insert question and its topic relationships
        
        Returns:
            Question UUID
        """
        # Insert question
        question_data = {
            'paper_id': paper_id,
            'question_number': question_number,
            'text': text,
            'marks': marks,
            'difficulty': difficulty,
            'qp_page_index': qp_page_index,
            'qp_page_count': qp_page_count,
            'page_pdf_url': page_pdf_url,
            'ms_page_indices': ms_page_indices,
            'ms_pdf_url': ms_pdf_url,
            'text_excerpt': text_excerpt,
            'has_diagram': has_diagram,
            'classification_confidence': classification_confidence,
            'subparts': subparts or []
        }
        
        question_result = self.insert('questions', question_data)
        question_id = question_result[0]['id']
        
        # Insert topic relationships
        if topics:
            # Get topic IDs
            topic_map = {}
            for topic_data in topics:
                topic_code = topic_data['topic_code']
                if topic_code not in topic_map:
                    topic_results = self.select('topics', 'id', {'code': topic_code}, limit=1)
                    if topic_results:
                        topic_map[topic_code] = topic_results[0]['id']
            
            # Create question_topics entries
            question_topics = []
            for topic_data in topics:
                topic_code = topic_data['topic_code']
                if topic_code in topic_map:
                    question_topics.append({
                        'question_id': question_id,
                        'topic_id': topic_map[topic_code],
                        'confidence': topic_data.get('confidence', 0.9),
                        'subpart_label': topic_data.get('subpart_label'),
                        'classification_method': topic_data.get('method', 'llm')
                    })
            
            if question_topics:
                self.insert('question_topics', question_topics)
        
        return question_id
    
    def upload_file(self, bucket: str, file_path: str, destination_path: str) -> str:
        """
        Upload a file to Supabase Storage
        
        Args:
            bucket: Storage bucket name (e.g., 'question-pdfs')
            file_path: Local file path to upload
            destination_path: Destination path in bucket (e.g., '2019/Jun/4PH1_Q1.pdf')
            
        Returns:
            Storage URL path (not full URL, just the path within bucket)
        """
        storage_url = f"{self.url}/storage/v1/object/{bucket}/{destination_path}"
        
        # Read file
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Upload with special headers for storage
        headers = {
            'apikey': self.key,
            'Authorization': f'Bearer {self.key}',
            'Content-Type': 'application/pdf',
            'x-upsert': 'true'  # Overwrite if exists
        }
        
        response = requests.post(storage_url, data=file_data, headers=headers)
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Storage upload failed: {response.status_code} - {response.text}")
        
        # Return the path (not full URL)
        return destination_path
    
    def get_public_url(self, bucket: str, file_path: str) -> str:
        """
        Get public URL for a file in storage
        
        Args:
            bucket: Storage bucket name
            file_path: File path within bucket
            
        Returns:
            Full public URL
        """
        return f"{self.url}/storage/v1/object/public/{bucket}/{file_path}"


# Test function
if __name__ == "__main__":
    # Test connection
    try:
        client = SupabaseClient()
        print(f"✅ Connected to Supabase: {client.url}")
        
        # Test select
        subjects = client.select('subjects', 'code,name', limit=5)
        print(f"✅ Found {len(subjects)} subjects:")
        for subject in subjects:
            print(f"   - {subject['code']}: {subject['name']}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
