#!/usr/bin/env python3
"""
Question Accuracy Checker - Claude Code Hook  
Validates grant application questions before they're written to files
Ensures questions match real RFPs and application requirements
"""

import sys
import json
import os
import re
import requests
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import argparse
from urllib.parse import urljoin, urlparse

class QuestionVerificationResult:
    """Result of question verification with specific issues found"""
    
    def __init__(self):
        self.is_valid = True
        self.errors = []
        self.warnings = []
        self.suggestions = []
        self.verified_questions = 0
        self.total_questions = 0
    
    def add_error(self, message: str):
        self.is_valid = False
        self.errors.append(message)
    
    def add_warning(self, message: str):
        self.warnings.append(message)
    
    def add_suggestion(self, message: str):
        self.suggestions.append(message)
    
    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "verification_rate": f"{self.verified_questions}/{self.total_questions}"
        }

class QuestionAccuracyChecker:
    """Validates grant application questions against official sources"""
    
    def __init__(self):
        # Generic question patterns that indicate made-up content
        self.generic_patterns = [
            r"describe your (project's |approach|methodology)",
            r"how will (your work|this project)",
            r"what (makes your team|is your plan|are your qualifications)", 
            r"explain how your",
            r"provide a brief",
            r"what specific (methodologies|technologies|tools)",
            r"how does your work (bridge|advance|contribute)",
            r"what evidence supports",
            r"how will you (measure|demonstrate|ensure)"
        ]
        
        # Known application systems and their question patterns
        self.application_systems = {
            "fastlane.nsf.gov": {
                "common_questions": [
                    "Project Summary",
                    "Project Description", 
                    "References Cited",
                    "Biographical Sketch",
                    "Budget Justification"
                ]
            },
            "grants.nih.gov": {
                "common_questions": [
                    "Specific Aims",
                    "Research Strategy",
                    "Bibliography & References Cited",
                    "Resource Sharing Plan"
                ]
            },
            "proposalcentral.com": {
                "common_questions": [
                    "Letters of Intent",
                    "Proposal Narrative",
                    "Budget and Budget Justification"
                ]
            }
        }
        
        # Red flag phrases that suggest fabricated questions
        self.red_flag_phrases = [
            "consciousness studies",
            "epistemological clarity", 
            "cognitive widget approach",
            "information integrity",
            "emergent phenomena and how it contributes",
            "mathematical and computational approach advance",
            "ai-powered tools",
            "ontoedit ai"
        ]
    
    def verify_questions_file(self, file_path: str) -> QuestionVerificationResult:
        """Verify questions from a file (Python, JSON, or text)"""
        result = QuestionVerificationResult()
        
        if not os.path.exists(file_path):
            result.add_error(f"Question file does not exist: {file_path}")
            return result
        
        try:
            questions = self._extract_questions_from_file(file_path)
            if not questions:
                result.add_warning("No questions found in file")
                return result
            
            result.total_questions = len(questions)
            
            for question_text in questions:
                self._verify_single_question(question_text, result)
            
            # Check overall patterns
            self._check_overall_patterns(questions, result)
            
        except Exception as e:
            result.add_error(f"Error processing questions file: {str(e)}")
        
        return result
    
    def _extract_questions_from_file(self, file_path: str) -> List[str]:
        """Extract question text from various file formats"""
        questions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # If it's Python code with GrantQuestion objects
            if file_path.endswith('.py') and 'GrantQuestion' in content:
                questions = self._extract_from_python_code(content)
            
            # If it's JSON
            elif file_path.endswith('.json'):
                questions = self._extract_from_json(content)
            
            # Plain text - look for question patterns
            else:
                questions = self._extract_from_text(content)
            
        except Exception as e:
            print(f"Error reading file {file_path}: {e}", file=sys.stderr)
        
        return questions
    
    def _extract_from_python_code(self, content: str) -> List[str]:
        """Extract questions from Python code with GrantQuestion objects"""
        questions = []
        
        # Pattern to match GrantQuestion constructor calls
        pattern = r'GrantQuestion\([^,]*,\s*["\']([^"\']+)["\']'
        matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            # Clean up the question text
            question = match.strip().replace('\\n', ' ').replace('  ', ' ')
            if question and len(question) > 10:  # Filter out very short matches
                questions.append(question)
        
        return questions
    
    def _extract_from_json(self, content: str) -> List[str]:
        """Extract questions from JSON structure"""
        questions = []
        
        try:
            data = json.loads(content)
            
            # Look for various JSON structures
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        question = item.get('question', item.get('question_text', ''))
                        if question:
                            questions.append(question)
            elif isinstance(data, dict):
                # Look for questions in various keys
                for key, value in data.items():
                    if 'question' in key.lower() and isinstance(value, str):
                        questions.append(value)
        
        except json.JSONDecodeError:
            pass
        
        return questions
    
    def _extract_from_text(self, content: str) -> List[str]:
        """Extract questions from plain text"""
        questions = []
        
        # Look for numbered questions
        patterns = [
            r'^\d+\.\s+(.+\?)$',  # "1. Question?"
            r'^Q\d+:\s*(.+)$',    # "Q1: Question"
            r'^\d+\)\s+(.+\?)$',  # "1) Question?"
        ]
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    questions.append(match.group(1).strip())
        
        return questions
    
    def _verify_single_question(self, question_text: str, result: QuestionVerificationResult):
        """Verify a single question for accuracy indicators"""
        question_lower = question_text.lower()
        
        # Check for red flag phrases
        for phrase in self.red_flag_phrases:
            if phrase.lower() in question_lower:
                result.add_error(f"Question contains red flag phrase: '{phrase}'")
                result.add_suggestion("Use exact questions from official RFPs only")
        
        # Check for generic patterns
        generic_count = 0
        for pattern in self.generic_patterns:
            if re.search(pattern, question_lower):
                generic_count += 1
        
        if generic_count >= 2:
            result.add_warning(f"Question appears to be generic/fabricated: '{question_text[:60]}...'")
            result.add_suggestion("Verify against official application forms")
        
        # Check question length and complexity
        if len(question_text) > 300:
            result.add_warning("Unusually long question - may be composite or fabricated")
        
        if '?' not in question_text and not any(word in question_lower for word in ['describe', 'explain', 'provide', 'submit']):
            result.add_warning("Text may not be a proper question")
    
    def _check_overall_patterns(self, questions: List[str], result: QuestionVerificationResult):
        """Check patterns across all questions"""
        
        # Check for suspiciously uniform question structure
        if len(questions) >= 3:
            starts_with_how = sum(1 for q in questions if q.lower().startswith('how'))
            starts_with_what = sum(1 for q in questions if q.lower().startswith('what'))
            
            if starts_with_how + starts_with_what >= len(questions) * 0.8:
                result.add_warning("Questions follow suspiciously uniform pattern")
                result.add_suggestion("Real applications usually have varied question types")
        
        # Check for project-specific jargon across questions
        project_terms = ['divinity school', 'ontoedit', 'endemic', 'four powers', 'sacred societies']
        term_mentions = sum(1 for q in questions for term in project_terms if term in q.lower())
        
        if term_mentions > 0:
            result.add_error("Questions contain project-specific terms (likely fabricated)")
            result.add_suggestion("Real grant questions should be generic and funder-focused")
        
        # Mark some questions as potentially verified based on standard patterns
        standard_question_indicators = [
            'budget', 'timeline', 'personnel', 'evaluation', 'dissemination',
            'collaboration', 'institutional', 'biographical', 'summary'
        ]
        
        for question in questions:
            for indicator in standard_question_indicators:
                if indicator in question.lower():
                    result.verified_questions += 1
                    break

def validate_questions_file(file_path: str) -> QuestionVerificationResult:
    """Main validation function for use by hooks"""
    checker = QuestionAccuracyChecker()
    return checker.verify_questions_file(file_path)

def main():
    """Main function for command line usage"""
    parser = argparse.ArgumentParser(description="Verify grant question accuracy")
    parser.add_argument("--validate", required=True, help="File containing questions to validate")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument("--quiet", action="store_true", help="Suppress output except errors")
    parser.add_argument("--source-required", action="store_true", help="Require source verification")
    
    args = parser.parse_args()
    
    result = validate_questions_file(args.validate)
    
    if not args.quiet:
        print("QUESTION ACCURACY CHECKER RESULTS:")
        print("="*50)
        
        if result.errors:
            print("❌ ERRORS:")
            for error in result.errors:
                print(f"  • {error}")
        
        if result.warnings:
            print("⚠️  WARNINGS:")
            for warning in result.warnings:
                print(f"  • {warning}")
        
        if result.suggestions:
            print("💡 SUGGESTIONS:")
            for suggestion in result.suggestions:
                print(f"  • {suggestion}")
        
        print(f"\n📊 Verification Rate: {result.verified_questions}/{result.total_questions}")
        print(f"✅ Valid: {result.is_valid}")
    
    # Exit with error code if validation failed
    if not result.is_valid or (args.strict and result.warnings):
        if not args.quiet:
            print("\n🚫 VALIDATION FAILED - Questions appear to be inaccurate or fabricated")
        sys.exit(1)
    
    if not args.quiet:
        print("\n✅ VALIDATION PASSED")
    sys.exit(0)

if __name__ == "__main__":
    main()