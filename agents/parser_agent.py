import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import pdfplumber
from docx import Document
import PyPDF2

@dataclass
class ResumeData:
    """Structured resume data"""
    original_path: str
    file_type: str
    raw_text: str
    sentences: List[str]
    metadata: Dict[str, Any]
    
class ResumeParserAgent:
    """Agent for parsing resumes from various formats"""
    
    def __init__(self, config):
        self.config = config
        self.supported_extensions = ['.pdf', '.docx', '.txt', '.doc']
        
    def parse_resume(self, file_path: str) -> ResumeData:
        """Parse a resume file into structured data"""
        
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        extension = path.suffix.lower()
        
        # Extract text based on file type
        if extension == '.pdf':
            text = self._parse_pdf(file_path)
        elif extension == '.docx':
            text = self._parse_docx(file_path)
        elif extension in ['.txt', '.doc']:
            text = self._parse_text(file_path)
        else:
            raise ValueError(f"Unsupported file type: {extension}")
            
        # Clean and segment text
        cleaned_text = self._clean_text(text)
        sentences = self._segment_sentences(cleaned_text)
        
        # Extract metadata
        metadata = self._extract_metadata(text, path)
        
        return ResumeData(
            original_path=str(path),
            file_type=extension,
            raw_text=cleaned_text,
            sentences=sentences,
            metadata=metadata
        )
    
    def _parse_pdf(self, file_path: str) -> str:
        """Parse PDF file"""
        text = ""
        
        # Try pdfplumber first (better for structured text)
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
        except:
            # Fallback to PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        
        return text
    
    def _parse_docx(self, file_path: str) -> str:
        """Parse DOCX file"""
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    
    def _parse_text(self, file_path: str) -> str:
        """Parse plain text file"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        return text
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,;:!?()-]', ' ', text)
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        return text.strip()
    
    def _segment_sentences(self, text: str) -> List[str]:
        """Segment text into sentences"""
        # Simple segmentation (can be enhanced with NLTK/spaCy)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _extract_metadata(self, text: str, path: Path) -> Dict:
        """Extract basic metadata"""
        return {
            "filename": path.name,
            "filesize": path.stat().st_size,
            "word_count": len(text.split()),
            "sentence_count": len(self._segment_sentences(text))
        }
    
    def save_to_json(self, resume_data: ResumeData, output_path: Optional[str] = None) -> str:
        """Save parsed resume to JSON format"""
        if output_path is None:
            output_path = os.path.join(
                self.config.processed_dir,
                f"{Path(resume_data.original_path).stem}.json"
            )
        
        data_dict = {
            "original_path": resume_data.original_path,
            "file_type": resume_data.file_type,
            "raw_text": resume_data.raw_text,
            "sentences": resume_data.sentences,
            "metadata": resume_data.metadata
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def batch_parse(self, input_dir: str) -> List[ResumeData]:
        """Parse all resumes in a directory"""
        input_path = Path(input_dir)
        parsed_resumes = []
        
        for ext in self.supported_extensions:
            for file_path in input_path.glob(f"*{ext}"):
                try:
                    print(f"Parsing: {file_path.name}")
                    resume_data = self.parse_resume(str(file_path))
                    parsed_resumes.append(resume_data)
                    
                    # Save to JSON
                    self.save_to_json(resume_data)
                    
                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")
        
        return parsed_resumes