#!/usr/bin/env python3
"""
Grant Question Extractor Module
Extracts application questions from grant websites and PDFs
"""

import re
import requests
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from bs4 import BeautifulSoup
import PyPDF2
from io import BytesIO
import json
import sys
import os

# Add parent directory to path to access Endemic Grant Agent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@dataclass
class GrantQuestion:
    """Represents a single grant application question"""
    question_number: int
    question_text: str
    question_type: str  # "short_answer", "essay", "budget", "timeline", "team"
    word_limit: Optional[int] = None
    char_limit: Optional[int] = None
    required: bool = True
    notes: Optional[str] = None

class GrantQuestionExtractor:
    """Extracts grant application questions from various sources"""
    
    def __init__(self):
        self.common_question_patterns = [
            r'^\d+\.\s+(.+\?)',  # Numbered questions
            r'^[A-Z]\.\s+(.+\?)',  # Letter-indexed questions
            r'^\*\s+(.+\?)',  # Bullet point questions
            r'^(?:Question|Q)\s*\d+:\s*(.+)',  # "Question 1:" format
            r'^(?:Please|Describe|Explain|Provide|Submit|Include)\s+(.+)',  # Command format
        ]
        
        self.foundation_specific_configs = {
            "Cosmos Institute": {
                "base_url": "https://cosmosgrants.org",
                "question_patterns": [
                    "Pitch yourself in 1-2 sentences",
                    "What is your innovative approach",
                    "How does this align with",
                    "What are your expected outcomes",
                    "Budget justification",
                    "Timeline and milestones",
                    "Team qualifications",
                    "Broader impacts statement"
                ]
            },
            "Templeton Foundation": {
                "base_url": "https://www.templeton.org",
                "question_patterns": [
                    "Project abstract",
                    "Statement of the problem",
                    "Project description",
                    "Expected outputs and outcomes",
                    "Project timeline",
                    "Budget narrative",
                    "Qualifications of project team"
                ]
            },
            "Mozilla Foundation": {
                "base_url": "https://foundation.mozilla.org",
                "question_patterns": [
                    "Project summary",
                    "Problem you're solving",
                    "Your solution approach",
                    "Impact metrics",
                    "Team background",
                    "Budget breakdown"
                ]
            },
            "NSF": {
                "base_url": "https://www.nsf.gov",
                "question_patterns": [
                    "Project Summary",
                    "Intellectual Merit",
                    "Broader Impacts",
                    "Project Description",
                    "References Cited",
                    "Biographical Sketches",
                    "Budget Justification",
                    "Data Management Plan"
                ]
            }
        }
    
    def extract_questions(self, grant_url: str, foundation_name: Optional[str] = None) -> List[GrantQuestion]:
        """
        Main entry point to extract questions from a grant opportunity
        """
        questions = []
        
        # Try PDF extraction if URL ends with .pdf
        if grant_url.endswith('.pdf'):
            questions = self.extract_from_pdf(grant_url)
        
        # Try web scraping for HTML pages
        elif grant_url.startswith('http'):
            questions = self.extract_from_webpage(grant_url)
        
        # If we have foundation-specific patterns, use those
        if foundation_name and foundation_name in self.foundation_specific_configs:
            foundation_questions = self.extract_from_foundation_config(foundation_name)
            if foundation_questions:
                questions = foundation_questions
        
        # If no questions found, use generic patterns
        if not questions:
            questions = self.generate_generic_questions(foundation_name)
        
        return questions
    
    def extract_from_webpage(self, url: str) -> List[GrantQuestion]:
        """Extract questions from a webpage"""
        questions = []
        
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for common question containers
            question_containers = soup.find_all(['ol', 'ul', 'div'], class_=re.compile(r'question|application|requirement', re.I))
            
            question_number = 1
            for container in question_containers:
                text_elements = container.find_all(['li', 'p', 'div'])
                for element in text_elements:
                    text = element.get_text(strip=True)
                    if self.is_likely_question(text):
                        questions.append(GrantQuestion(
                            question_number=question_number,
                            question_text=text,
                            question_type=self.classify_question(text),
                            word_limit=self.extract_word_limit(text)
                        ))
                        question_number += 1
            
            # Also look for forms
            forms = soup.find_all('form')
            for form in forms:
                labels = form.find_all('label')
                for label in labels:
                    text = label.get_text(strip=True)
                    if text and len(text) > 10:
                        questions.append(GrantQuestion(
                            question_number=question_number,
                            question_text=text,
                            question_type="short_answer",
                            required=True
                        ))
                        question_number += 1
        
        except Exception as e:
            print(f"Error extracting from webpage: {e}")
        
        return questions
    
    def extract_from_pdf(self, pdf_url: str) -> List[GrantQuestion]:
        """Extract questions from a PDF document"""
        questions = []
        
        try:
            response = requests.get(pdf_url, timeout=10)
            pdf_file = BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text()
            
            # Extract questions from PDF text
            lines = full_text.split('\n')
            question_number = 1
            
            for line in lines:
                line = line.strip()
                if self.is_likely_question(line):
                    questions.append(GrantQuestion(
                        question_number=question_number,
                        question_text=line,
                        question_type=self.classify_question(line),
                        word_limit=self.extract_word_limit(line)
                    ))
                    question_number += 1
        
        except Exception as e:
            print(f"Error extracting from PDF: {e}")
        
        return questions
    
    def extract_from_foundation_config(self, foundation_name: str) -> List[GrantQuestion]:
        """Use foundation-specific configurations to extract questions"""
        questions = []
        
        if foundation_name in self.foundation_specific_configs:
            config = self.foundation_specific_configs[foundation_name]
            patterns = config.get("question_patterns", [])
            
            for i, pattern in enumerate(patterns, 1):
                question_type = self.classify_question(pattern)
                word_limit = None
                
                # Set word limits based on question type
                if "abstract" in pattern.lower() or "summary" in pattern.lower():
                    word_limit = 150
                elif "description" in pattern.lower() or "narrative" in pattern.lower():
                    word_limit = 500
                elif "pitch" in pattern.lower() or "sentence" in pattern.lower():
                    word_limit = 50
                
                questions.append(GrantQuestion(
                    question_number=i,
                    question_text=pattern,
                    question_type=question_type,
                    word_limit=word_limit,
                    required=True
                ))
        
        return questions
    
    def is_likely_question(self, text: str) -> bool:
        """Determine if a text string is likely a question"""
        if not text or len(text) < 10:
            return False
        
        # Check for question marks
        if '?' in text:
            return True
        
        # Check for common question starters
        question_starters = [
            'describe', 'explain', 'provide', 'what', 'why', 'how',
            'please', 'submit', 'include', 'list', 'identify',
            'outline', 'summarize', 'detail', 'specify'
        ]
        
        text_lower = text.lower()
        for starter in question_starters:
            if text_lower.startswith(starter):
                return True
        
        # Check against patterns
        for pattern in self.common_question_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def classify_question(self, question_text: str) -> str:
        """Classify the type of question"""
        text_lower = question_text.lower()
        
        if any(word in text_lower for word in ['budget', 'cost', 'expense', 'funding']):
            return "budget"
        elif any(word in text_lower for word in ['timeline', 'milestone', 'schedule', 'when']):
            return "timeline"
        elif any(word in text_lower for word in ['team', 'qualification', 'experience', 'cv', 'bio']):
            return "team"
        elif any(word in text_lower for word in ['abstract', 'summary', 'pitch', '1-2 sentence']):
            return "short_answer"
        else:
            return "essay"
    
    def extract_word_limit(self, text: str) -> Optional[int]:
        """Extract word limit from question text"""
        # Look for patterns like "500 words", "max 500 words", "500-word limit"
        patterns = [
            r'(\d+)\s*words?\s*(?:max|maximum)?',
            r'(?:max|maximum)\s*(\d+)\s*words?',
            r'(\d+)-word\s*(?:limit|maximum)?',
            r'(?:up to|no more than)\s*(\d+)\s*words?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    def generate_generic_questions(self, foundation_name: Optional[str] = None) -> List[GrantQuestion]:
        """Generate generic grant application questions as fallback"""
        generic_questions = [
            GrantQuestion(1, "Project Title and Summary (150 words)", "short_answer", word_limit=150),
            GrantQuestion(2, "Problem Statement: What problem are you solving?", "essay", word_limit=500),
            GrantQuestion(3, "Proposed Solution: Describe your approach", "essay", word_limit=750),
            GrantQuestion(4, "Expected Outcomes and Impact", "essay", word_limit=500),
            GrantQuestion(5, "Project Timeline and Milestones", "timeline", word_limit=500),
            GrantQuestion(6, "Budget Narrative and Justification", "budget", word_limit=500),
            GrantQuestion(7, "Team Qualifications and Experience", "team", word_limit=500),
            GrantQuestion(8, "Evaluation and Success Metrics", "essay", word_limit=300),
            GrantQuestion(9, "Sustainability Plan", "essay", word_limit=300),
            GrantQuestion(10, "Additional Information or Special Circumstances", "essay", word_limit=200, required=False)
        ]
        
        return generic_questions
    
    def format_questions_for_notion(self, questions: List[GrantQuestion]) -> str:
        """Format questions for display in Notion"""
        formatted = "# Grant Application Questions\n\n"
        
        for q in questions:
            formatted += f"## Question {q.question_number}"
            if q.word_limit:
                formatted += f" (Max {q.word_limit} words)"
            if not q.required:
                formatted += " [Optional]"
            formatted += f"\n\n**{q.question_text}**\n\n"
            formatted += f"*Type: {q.question_type.replace('_', ' ').title()}*\n\n---\n\n"
        
        return formatted


def main():
    """Test the question extractor"""
    extractor = GrantQuestionExtractor()
    
    # Test with Cosmos Institute
    print("Testing Cosmos Institute questions:")
    questions = extractor.extract_from_foundation_config("Cosmos Institute")
    for q in questions:
        print(f"{q.question_number}. {q.question_text} ({q.question_type}, {q.word_limit} words)")
    
    print("\n" + "="*50 + "\n")
    
    # Format for Notion
    notion_format = extractor.format_questions_for_notion(questions)
    print("Notion formatted version:")
    print(notion_format)


if __name__ == "__main__":
    main()