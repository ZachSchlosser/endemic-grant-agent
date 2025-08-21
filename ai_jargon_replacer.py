#!/usr/bin/env python3
"""
AI Jargon Replacement Hook System for Endemic Grant Agent

This script detects common AI writing patterns and replaces them with more natural,
human-sounding alternatives. It can analyze reference documents for style matching
and provides comprehensive jargon detection and replacement.

Usage:
    python ai_jargon_replacer.py <input_file> [--reference <ref_file>] [--output <output_file>]
    python ai_jargon_replacer.py --text "Text to analyze" [--reference <ref_file>]

Features:
- Detects overused AI phrases and buzzwords
- Analyzes em dash usage patterns
- Reference document style matching
- Context-aware replacements
- Detailed change reporting
"""

import re
import argparse
import sys
import json
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from urllib.parse import urlparse
import os

@dataclass
class StyleProfile:
    """Represents the style characteristics of a reference document"""
    avg_sentence_length: float
    formal_words_ratio: float
    transition_words_ratio: float
    em_dash_frequency: float
    common_words: Set[str]
    tone_indicators: Dict[str, int]
    
@dataclass
class JargonMatch:
    """Represents a detected jargon pattern"""
    original: str
    replacement: str
    start_pos: int
    end_pos: int
    category: str
    confidence: float

class AIJargonReplacer:
    """Main class for detecting and replacing AI jargon patterns"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize with configuration file or defaults"""
        self.config = self._load_config(config_path)
        self.overused_phrases = self.config.get('overused_phrases', {
            'delve into': ['explore', 'examine', 'look at', 'investigate'],
            'furthermore': ['also', 'additionally', 'next'],
            'moreover': ['also', 'what\'s more', 'in addition'],
            'in conclusion': ['finally', 'to sum up', 'in summary'],
            'groundbreaking': ['new', 'novel', 'first', 'pioneering'],
            'revolutionary': ['significant', 'major', 'transformative'],
            'transformative': ['significant', 'meaningful', 'impactful'],
            'innovative': ['new', 'creative', 'original'],
            'leverage': ['use', 'utilize', 'apply', 'employ'],
            'seamless': ['smooth', 'integrated', 'unified'],
            'paradigm': ['model', 'framework', 'approach'],
            'cutting-edge': ['advanced', 'latest', 'modern'],
            'state-of-the-art': ['advanced', 'current', 'leading'],
            'game-changing': ['significant', 'important', 'major'],
            'disruptive': ['changing', 'influential', 'impactful'],
            'synergy': ['cooperation', 'collaboration', 'teamwork'],
            'holistic': ['comprehensive', 'complete', 'integrated'],
            'optimize': ['improve', 'enhance', 'refine'],
            'streamline': ['simplify', 'improve', 'make efficient'],
            'robust': ['strong', 'reliable', 'solid'],
            'scalable': ['expandable', 'adaptable', 'flexible'],
            'dynamic': ['changing', 'active', 'flexible'],
            'comprehensive': ['complete', 'thorough', 'full'],
            'multifaceted': ['complex', 'varied', 'diverse'],
            'pivotal': ['crucial', 'key', 'essential'],
            'unprecedented': ['new', 'unique', 'first'],
            'exponential': ['rapid', 'significant', 'substantial'],
            'paradigm shift': ['major change', 'transformation', 'shift'],
            'game changer': ['significant factor', 'key element', 'major influence'],
            'next level': ['improved', 'enhanced', 'advanced'],
            'best practices': ['proven methods', 'effective approaches', 'good techniques'],
        })
        
        self.transition_patterns = self.config.get('transition_patterns', [
            r'\b(furthermore|moreover|additionally|consequently|nevertheless|nonetheless|therefore|thus|hence)\b',
            r'\b(in conclusion|to conclude|in summary|to summarize|in essence)\b',
            r'\b(on the other hand|in contrast|conversely|alternatively)\b',
            r'\b(for instance|for example|such as|namely|specifically)\b'
        ])
        
        self.buzzword_clusters = self.config.get('buzzword_clusters', [
            ['innovative', 'groundbreaking', 'revolutionary'],
            ['leverage', 'utilize', 'optimize'],
            ['seamless', 'integrated', 'comprehensive'],
            ['transformative', 'paradigm', 'disruptive']
        ])
        
        self.em_dash_threshold = self.config.get('em_dash_threshold', 2)
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or return defaults"""
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load config file {config_path}: {e}")
        
        return {}
    
    def analyze_text(self, text: str, reference_style: Optional[StyleProfile] = None) -> Tuple[str, List[JargonMatch]]:
        """Analyze text and return cleaned version with list of changes"""
        matches = []
        cleaned_text = text
        
        # Detect overused phrases
        phrase_matches = self._detect_overused_phrases(cleaned_text)
        matches.extend(phrase_matches)
        
        # Apply phrase replacements
        for match in sorted(phrase_matches, key=lambda x: x.start_pos, reverse=True):
            cleaned_text = (cleaned_text[:match.start_pos] + 
                          match.replacement + 
                          cleaned_text[match.end_pos:])
        
        # Detect excessive em dashes
        em_dash_matches = self._detect_excessive_em_dashes(cleaned_text)
        matches.extend(em_dash_matches)
        
        # Apply em dash fixes
        for match in sorted(em_dash_matches, key=lambda x: x.start_pos, reverse=True):
            cleaned_text = (cleaned_text[:match.start_pos] + 
                          match.replacement + 
                          cleaned_text[match.end_pos:])
        
        # Detect formal transition overuse
        transition_matches = self._detect_formal_transitions(cleaned_text)
        matches.extend(transition_matches)
        
        # Apply transition replacements
        for match in sorted(transition_matches, key=lambda x: x.start_pos, reverse=True):
            cleaned_text = (cleaned_text[:match.start_pos] + 
                          match.replacement + 
                          cleaned_text[match.end_pos:])
        
        # Detect buzzword clustering
        cluster_matches = self._detect_buzzword_clustering(cleaned_text)
        matches.extend(cluster_matches)
        
        # Apply cluster fixes
        for match in sorted(cluster_matches, key=lambda x: x.start_pos, reverse=True):
            cleaned_text = (cleaned_text[:match.start_pos] + 
                          match.replacement + 
                          cleaned_text[match.end_pos:])
        
        # Style matching adjustments if reference provided
        if reference_style:
            cleaned_text, style_matches = self._apply_style_matching(cleaned_text, reference_style)
            matches.extend(style_matches)
        
        return cleaned_text, matches
    
    def _detect_overused_phrases(self, text: str) -> List[JargonMatch]:
        """Detect and prepare replacements for overused phrases"""
        matches = []
        
        for phrase, replacements in self.overused_phrases.items():
            pattern = r'\b' + re.escape(phrase) + r'\b'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Choose replacement based on context or randomly
                replacement = self._choose_replacement(phrase, replacements, text, match.start())
                
                matches.append(JargonMatch(
                    original=match.group(),
                    replacement=replacement,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    category='overused_phrase',
                    confidence=0.9
                ))
        
        return matches
    
    def _detect_excessive_em_dashes(self, text: str) -> List[JargonMatch]:
        """Enhanced em dash detection with typography rules from utility scripts"""
        matches = []
        
        # First, apply hyphenation fixes
        typography_rules = self.config.get('typography_rules', {})
        em_dash_patterns = typography_rules.get('em_dash_patterns', {})
        
        # Fix common hyphenation issues
        hyphenation_fixes = em_dash_patterns.get('hyphenation_fixes', [])
        for fix in hyphenation_fixes:
            if fix['from'] in text:
                matches.append(JargonMatch(
                    original=fix['from'],
                    replacement=fix['to'],
                    start_pos=text.find(fix['from']),
                    end_pos=text.find(fix['from']) + len(fix['from']),
                    category='hyphenation_fix',
                    confidence=0.9
                ))
        
        # Apply definition patterns (cognitive widgets, OntoEdit AI, etc.)
        definition_patterns = em_dash_patterns.get('definition_patterns', [])
        for pattern_config in definition_patterns:
            pattern = pattern_config['pattern']
            replacement = pattern_config['replacement']
            description = pattern_config['description']
            
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Handle capitalization preservation
                old_text = match.group(0)
                if 'The first tool that' in replacement:
                    new_text = re.sub(pattern, replacement, old_text, flags=re.IGNORECASE)
                    new_text = new_text.replace('the first tool that', 'The first tool that')
                elif 'An AI system' in replacement:
                    new_text = re.sub(pattern, replacement, old_text, flags=re.IGNORECASE)
                    new_text = new_text.replace('an AI system', 'An AI system')
                else:
                    new_text = re.sub(pattern, replacement, old_text, flags=re.IGNORECASE)
                
                matches.append(JargonMatch(
                    original=old_text,
                    replacement=new_text,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    category=f'definition_pattern_{description.lower().replace(" ", "_")}',
                    confidence=0.9
                ))
        
        # Count em dashes and apply general reduction if needed
        em_dash_count = text.count('—')
        target_max = em_dash_patterns.get('target_max_per_document', 6)
        
        if em_dash_count > target_max:
            # Find remaining em dashes and convert the least impactful ones
            strategies = em_dash_patterns.get('replacement_strategies', {})
            
            for match in re.finditer(r'([^—\n]{10,50})\s*—\s*([^—\n]{10,50})', text):
                if len([m for m in matches if m.category.startswith('em_dash_')]) >= (em_dash_count - target_max):
                    break
                    
                old_text = match.group(0)
                left_part = match.group(1).strip()
                right_part = match.group(2).strip()
                
                # Apply intelligent replacement strategy
                if right_part and right_part[0].isupper():
                    # Sentence break strategy
                    new_text = f"{left_part}. {right_part}"
                    strategy = strategies.get('sentence_break', {}).get('description', 'Period for sentence break')
                elif any(word in right_part.lower()[:15] for word in strategies.get('connection', {}).get('connector_words', ['and', 'but', 'which', 'that'])):
                    # Connection strategy
                    new_text = f"{left_part}, {right_part}"
                    strategy = strategies.get('connection', {}).get('description', 'Comma for connection')
                else:
                    # Default strategy
                    new_text = f"{left_part}, {right_part}"
                    strategy = strategies.get('default', {}).get('description', 'Default comma')
                
                matches.append(JargonMatch(
                    original=old_text,
                    replacement=new_text,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    category=f'em_dash_reduction_{strategy.lower().replace(" ", "_")}',
                    confidence=0.8
                ))
        
        return matches
    
    def _detect_formal_transitions(self, text: str) -> List[JargonMatch]:
        """Detect overly formal transition words"""
        matches = []
        
        for pattern in self.transition_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                word = match.group(1).lower()
                replacement = self._get_casual_transition(word)
                
                if replacement:
                    matches.append(JargonMatch(
                        original=match.group(1),
                        replacement=replacement,
                        start_pos=match.start(1),
                        end_pos=match.end(1),
                        category='formal_transition',
                        confidence=0.8
                    ))
        
        return matches
    
    def _detect_buzzword_clustering(self, text: str) -> List[JargonMatch]:
        """Detect clusters of buzzwords in close proximity"""
        matches = []
        
        # Look for multiple buzzwords in the same sentence or paragraph
        sentences = re.split(r'[.!?]+', text)
        
        for i, sentence in enumerate(sentences):
            for cluster in self.buzzword_clusters:
                found_words = []
                for word in cluster:
                    pattern = r'\b' + re.escape(word) + r'\b'
                    if re.search(pattern, sentence, re.IGNORECASE):
                        found_words.append(word)
                
                # If more than one buzzword from same cluster, suggest removing some
                if len(found_words) > 1:
                    # Find the position in original text
                    sentence_start = text.find(sentence.strip())
                    if sentence_start != -1:
                        # Keep the first buzzword, replace others with simpler alternatives
                        for j, word in enumerate(found_words[1:], 1):
                            word_pattern = r'\b' + re.escape(word) + r'\b'
                            word_match = re.search(word_pattern, sentence, re.IGNORECASE)
                            if word_match:
                                simple_replacement = self._get_simple_alternative(word)
                                matches.append(JargonMatch(
                                    original=word_match.group(),
                                    replacement=simple_replacement,
                                    start_pos=sentence_start + word_match.start(),
                                    end_pos=sentence_start + word_match.end(),
                                    category='buzzword_cluster',
                                    confidence=0.6
                                ))
        
        return matches
    
    def _choose_replacement(self, phrase: str, replacements: List[str], text: str, position: int) -> str:
        """Choose the best replacement based on context"""
        # Simple context analysis - look at surrounding words
        context_window = 100
        start = max(0, position - context_window)
        end = min(len(text), position + len(phrase) + context_window)
        context = text[start:end].lower()
        
        # Basic heuristics for replacement selection
        if 'research' in context or 'study' in context:
            # Prefer more academic alternatives
            academic_words = ['examine', 'investigate', 'analyze']
            for replacement in replacements:
                if replacement in academic_words:
                    return replacement
        
        if 'business' in context or 'market' in context:
            # Prefer business-friendly alternatives
            business_words = ['utilize', 'employ', 'apply']
            for replacement in replacements:
                if replacement in business_words:
                    return replacement
        
        # Default to first replacement
        return replacements[0]
    
    def _get_casual_transition(self, formal_word: str) -> Optional[str]:
        """Get casual alternatives for formal transitions"""
        casual_transitions = {
            'furthermore': 'Also',
            'moreover': 'Plus',
            'additionally': 'Also',
            'consequently': 'So',
            'nevertheless': 'But',
            'nonetheless': 'Still',
            'therefore': 'So',
            'thus': 'This way',
            'hence': 'So',
            'in conclusion': 'Finally',
            'to conclude': 'In the end',
            'in summary': 'To sum up',
            'to summarize': 'In short',
            'in essence': 'Basically'
        }
        
        return casual_transitions.get(formal_word.lower())
    
    def _get_simple_alternative(self, buzzword: str) -> str:
        """Get simple alternatives for buzzwords"""
        simple_alternatives = {
            'innovative': 'new',
            'groundbreaking': 'first',
            'revolutionary': 'big',
            'leverage': 'use',
            'utilize': 'use',
            'optimize': 'improve',
            'seamless': 'smooth',
            'integrated': 'connected',
            'comprehensive': 'complete',
            'transformative': 'important',
            'paradigm': 'model',
            'disruptive': 'changing',
            'cutting-edge': 'latest',
            'state-of-the-art': 'advanced',
            'game-changing': 'important',
            'synergy': 'teamwork',
            'holistic': 'complete',
            'streamline': 'simplify',
            'robust': 'strong',
            'scalable': 'flexible',
            'dynamic': 'active'
        }
        
        return simple_alternatives.get(buzzword.lower(), buzzword)
    
    def _apply_style_matching(self, text: str, reference_style: StyleProfile) -> Tuple[str, List[JargonMatch]]:
        """Apply style matching based on reference document"""
        matches = []
        modified_text = text
        
        # Analyze current text style
        current_style = self.analyze_style(text)
        
        # Adjust sentence length if needed
        if abs(current_style.avg_sentence_length - reference_style.avg_sentence_length) > 5:
            # Split or combine sentences as needed
            modified_text, length_matches = self._adjust_sentence_length(
                modified_text, reference_style.avg_sentence_length
            )
            matches.extend(length_matches)
        
        # Adjust formality level
        if abs(current_style.formal_words_ratio - reference_style.formal_words_ratio) > 0.1:
            modified_text, formality_matches = self._adjust_formality(
                modified_text, reference_style.formal_words_ratio
            )
            matches.extend(formality_matches)
        
        return modified_text, matches
    
    def analyze_style(self, text: str) -> StyleProfile:
        """Analyze the style characteristics of given text"""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Calculate average sentence length
        total_words = sum(len(sentence.split()) for sentence in sentences)
        avg_sentence_length = total_words / len(sentences) if sentences else 0
        
        # Count formal words
        formal_words = ['furthermore', 'moreover', 'consequently', 'nevertheless', 'therefore']
        formal_count = sum(text.lower().count(word) for word in formal_words)
        formal_words_ratio = formal_count / total_words if total_words > 0 else 0
        
        # Count transition words
        transition_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in self.transition_patterns)
        transition_words_ratio = transition_count / total_words if total_words > 0 else 0
        
        # Count em dashes
        em_dash_count = len(re.findall(r'—', text))
        em_dash_frequency = em_dash_count / len(sentences) if sentences else 0
        
        # Extract common words (simplified)
        words = re.findall(r'\b\w+\b', text.lower())
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        common_words = set(word for word, freq in word_freq.items() if freq > 2)
        
        # Basic tone indicators
        tone_indicators = {
            'academic': len(re.findall(r'\b(research|study|analysis|methodology)\b', text.lower())),
            'business': len(re.findall(r'\b(strategy|market|revenue|customer)\b', text.lower())),
            'casual': len(re.findall(r'\b(really|pretty|quite|kind of)\b', text.lower()))
        }
        
        return StyleProfile(
            avg_sentence_length=avg_sentence_length,
            formal_words_ratio=formal_words_ratio,
            transition_words_ratio=transition_words_ratio,
            em_dash_frequency=em_dash_frequency,
            common_words=common_words,
            tone_indicators=tone_indicators
        )
    
    def _adjust_sentence_length(self, text: str, target_length: float) -> Tuple[str, List[JargonMatch]]:
        """Adjust sentence length to match target"""
        matches = []
        # This is a simplified implementation
        # In practice, you'd want more sophisticated sentence manipulation
        return text, matches
    
    def _adjust_formality(self, text: str, target_formality: float) -> Tuple[str, List[JargonMatch]]:
        """Adjust formality level to match target"""
        matches = []
        # This is a simplified implementation
        # In practice, you'd want more sophisticated formality adjustment
        return text, matches
    
    def analyze_reference_document(self, doc_path_or_url: str) -> StyleProfile:
        """Analyze a reference document to create a style profile"""
        try:
            if doc_path_or_url.startswith(('http://', 'https://')):
                text = self._fetch_url_content(doc_path_or_url)
            else:
                with open(doc_path_or_url, 'r', encoding='utf-8') as f:
                    text = f.read()
            
            return self.analyze_style(text)
        
        except Exception as e:
            print(f"Error analyzing reference document: {e}")
            return None
    
    def _fetch_url_content(self, url: str) -> str:
        """Fetch content from URL (simplified - you might want to use a proper scraper)"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Basic HTML stripping (you might want to use BeautifulSoup for better results)
            text = re.sub(r'<[^>]+>', '', response.text)
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
        except Exception as e:
            raise Exception(f"Could not fetch URL content: {e}")
    
    def generate_report(self, matches: List[JargonMatch]) -> str:
        """Generate a detailed report of changes made"""
        if not matches:
            return "No AI jargon patterns detected. Text appears natural."
        
        report = ["AI JARGON ANALYSIS REPORT", "=" * 30, ""]
        
        # Group by category
        categories = {}
        for match in matches:
            if match.category not in categories:
                categories[match.category] = []
            categories[match.category].append(match)
        
        for category, category_matches in categories.items():
            report.append(f"{category.upper().replace('_', ' ')} ({len(category_matches)} issues)")
            report.append("-" * 40)
            
            for match in category_matches:
                report.append(f"• '{match.original}' → '{match.replacement}' (confidence: {match.confidence:.1f})")
            
            report.append("")
        
        report.append(f"TOTAL CHANGES: {len(matches)}")
        report.append("")
        
        return "\n".join(report)

def main():
    """Main command-line interface"""
    parser = argparse.ArgumentParser(
        description="AI Jargon Replacement Hook System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ai_jargon_replacer.py proposal.txt
  python ai_jargon_replacer.py proposal.txt --reference style_guide.txt
  python ai_jargon_replacer.py --text "This groundbreaking approach will leverage innovative solutions"
  python ai_jargon_replacer.py proposal.txt --output cleaned_proposal.txt --report
        """
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('input_file', nargs='?', help='Input file to analyze')
    input_group.add_argument('--text', help='Text string to analyze')
    
    # Optional arguments
    parser.add_argument('--reference', help='Reference document/URL for style matching')
    parser.add_argument('--output', help='Output file for cleaned text')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--report', action='store_true', help='Generate detailed report')
    parser.add_argument('--quiet', action='store_true', help='Suppress output except errors')
    
    args = parser.parse_args()
    
    try:
        # Initialize replacer
        replacer = AIJargonReplacer(args.config)
        
        # Get input text
        if args.input_file:
            with open(args.input_file, 'r', encoding='utf-8') as f:
                input_text = f.read()
        else:
            input_text = args.text
        
        # Analyze reference document if provided
        reference_style = None
        if args.reference:
            reference_style = replacer.analyze_reference_document(args.reference)
            if reference_style and not args.quiet:
                print(f"Reference style analyzed: {args.reference}")
        
        # Analyze and clean text
        cleaned_text, matches = replacer.analyze_text(input_text, reference_style)
        
        # Output results
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
            if not args.quiet:
                print(f"Cleaned text written to: {args.output}")
        else:
            print(cleaned_text)
        
        # Generate report if requested
        if args.report or not args.quiet:
            report = replacer.generate_report(matches)
            if args.report:
                report_file = (args.output or args.input_file or 'analysis') + '_report.txt'
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                if not args.quiet:
                    print(f"\nReport written to: {report_file}")
            elif not args.quiet:
                print("\n" + report)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()