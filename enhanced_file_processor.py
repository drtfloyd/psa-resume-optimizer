"""
Enhanced File Processing Module for PSA Resume Optimizer
Supports PDF, DOCX, TXT, OCR, and advanced text extraction
"""

import streamlit as st
import io
import tempfile
import os
from typing import Dict, List, Optional, Tuple
import hashlib
import json
from datetime import datetime, timedelta

# Basic enhanced file processor
class EnhancedFileProcessor:
    def __init__(self, cache_dir: str = "file_cache"):
        self.cache_dir = cache_dir
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        os.makedirs(cache_dir, exist_ok=True)

    def extract_text_from_file(self, file) -> Tuple[str, Dict]:
        """Enhanced file text extraction with better support"""
        
        if not self.validate_file(file):
            return "", {}

        metadata = {
            'file_name': file.name,
            'file_size': file.size,
            'file_type': file.type,
            'extraction_method': 'enhanced',
            'word_count': 0,
            'extraction_timestamp': datetime.now().isoformat()
        }

        try:
            if file.type == "application/pdf":
                text = self._extract_from_pdf(file)
                metadata['extraction_method'] = 'pdf_enhanced'
            elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                text = self._extract_from_docx(file)
                metadata['extraction_method'] = 'docx'
            elif file.type == "text/plain":
                text = self._extract_from_text(file)
                metadata['extraction_method'] = 'text'
            else:
                st.error(f"Unsupported file type: {file.type}")
                return "", metadata

            metadata['word_count'] = len(text.split())
            return text, metadata

        except Exception as e:
            st.error(f"Error extracting text from {file.name}: {str(e)}")
            return "", metadata

    def _extract_from_pdf(self, file) -> str:
        """Extract text from PDF"""
        try:
            from PyPDF2 import PdfReader
            
            file_stream = io.BytesIO(file.getvalue())
            reader = PdfReader(file_stream)
            text_parts = []
            
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            return "\n".join(text_parts)
        except Exception as e:
            st.warning(f"PDF extraction error: {str(e)}")
            return ""

    def _extract_from_docx(self, file) -> str:
        """Extract text from DOCX files"""
        try:
            from docx import Document
            
            file_stream = io.BytesIO(file.getvalue())
            doc = Document(file_stream)
            
            text_parts = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            
            return "\n".join(text_parts)
        except Exception as e:
            st.warning(f"DOCX extraction error: {str(e)}")
            return ""

    def _extract_from_text(self, file) -> str:
        """Extract text from plain text files"""
        try:
            return str(file.getvalue(), "utf-8")
        except UnicodeDecodeError:
            try:
                return str(file.getvalue(), "latin-1")
            except Exception as e:
                st.warning(f"Text extraction error: {str(e)}")
                return ""

    def validate_file(self, file) -> bool:
        """Enhanced file validation"""
        if file is None:
            return False
            
        if file.size > self.max_file_size:
            st.error(f"File '{file.name}' is too large. Maximum size: {self.max_file_size // (1024*1024)}MB")
            return False
            
        valid_types = [
            "application/pdf",
            "text/plain",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ]
        
        if file.type not in valid_types:
            st.error(f"Invalid file type '{file.type}'. Supported: PDF, DOCX, TXT")
            return False
            
        return True

# Global instance
file_processor = EnhancedFileProcessor()