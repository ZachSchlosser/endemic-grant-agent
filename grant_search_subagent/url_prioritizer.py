#!/usr/bin/env python3
"""
URL Prioritization System for Grant Discovery
Intelligently prioritizes URLs for scraping based on relevance and quality indicators
"""

import re
from typing import List, Dict, Tuple, Set, Optional
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import GrantAgentLogger

@dataclass
class URLScore:
    """Scoring information for a URL"""
    url: str
    relevance_score: float
    quality_score: float
    priority_score: float
    reasoning: List[str]
    category: str

class URLPrioritizer:
    """
    Intelligent URL prioritization for grant discovery
    Scores URLs based on:
    1. Grant-specific keywords and indicators
    2. Domain authority and reliability
    3. Content freshness indicators
    4. Funding amount indicators
    5. Application deadline proximity
    """
    
    def __init__(self):
        """Initialize the URL prioritizer"""
        self.logger = GrantAgentLogger().get_logger("url_prioritizer")
        
        # High-priority grant keywords
        self.high_priority_keywords = {
            'funding', 'grant', 'awards', 'fellowship', 'scholarship',
            'opportunities', 'rfp', 'solicitation', 'application',
            'proposal', 'submission', 'deadline', 'open-call'
        }
        
        # Education and research specific terms
        self.education_keywords = {
            'education', 'leadership', 'curriculum', 'learning', 'training',
            'development', 'capacity', 'institutional', 'transformation',
            'innovation', 'research', 'academic', 'university', 'school'
        }
        
        # AI and technology terms
        self.ai_keywords = {
            'artificial-intelligence', 'ai', 'machine-learning', 'technology',
            'digital', 'computational', 'algorithm', 'automation', 'future',
            'emerging', 'advanced', 'intelligent', 'cognitive'
        }
        
        # High-quality domains (known funders and foundations)
        self.trusted_domains = {
            # Government agencies
            'nsf.gov': 10.0,
            'nih.gov': 10.0,
            'ed.gov': 9.5,
            'energy.gov': 9.0,
            'neh.gov': 9.0,
            'nea.gov': 8.5,
            'state.gov': 8.0,
            
            # Major foundations
            'gatesfoundation.org': 10.0,
            'fordfoundation.org': 9.5,
            'rockefellerfoundation.org': 9.5,
            'kresge.org': 9.0,
            'macfound.org': 9.5,
            'rwjf.org': 9.0,
            'carnegie.org': 9.5,
            'knightfoundation.org': 9.0,
            
            # Tech philanthropy
            'chanzuckerberg.com': 10.0,
            'mozilla.org': 8.5,
            'omidyar.com': 8.5,
            'templeton.org': 9.0,
            'simonsfoundation.org': 9.5,
            
            # Research institutions
            'harvard.edu': 8.0,
            'mit.edu': 8.0,
            'stanford.edu': 8.0,
            'berkeley.edu': 7.5,
            'princeton.edu': 8.0,
            'yale.edu': 8.0,
            
            # Grant aggregators and databases
            'grants.gov': 10.0,
            'fundingalerts.com': 7.0,
            'pivot.cos.com': 7.5,
            'researchprofessional.com': 7.0,
            'candid.org': 8.0,  # Foundation Directory Online
            'grantspace.org': 7.5
        }
        
        # Indicators of high-value grants
        self.high_value_indicators = [
            r'\$\d{1,3}(?:,\d{3})*(?:,\d{3})*',  # Dollar amounts
            r'\d+\s*million',
            r'\d+M',
            r'multi-year',
            r'transformative',
            r'breakthrough',
            r'revolutionary',
            r'innovative',
            r'cutting-edge'
        ]
        
        # Time-sensitive indicators
        self.urgency_indicators = [
            r'deadline',
            r'due\s+\w+\s+\d{1,2}',
            r'closes?\s+\w+\s+\d{1,2}',
            r'application\s+period',
            r'limited\s+time',
            r'expires?',
            r'final\s+call'
        ]
        
        # Quality indicators in URLs
        self.quality_url_patterns = [
            r'/funding',
            r'/grants',
            r'/opportunities',
            r'/awards',
            r'/apply',
            r'/application',
            r'/rfp',
            r'/solicitation'
        ]
        
        self.logger.info("Initialized URLPrioritizer with comprehensive scoring system")
    
    def prioritize_urls(self, urls: List[str], context_keywords: Optional[Set[str]] = None) -> List[URLScore]:
        """
        Prioritize a list of URLs for scraping
        
        Args:
            urls: List of URLs to prioritize
            context_keywords: Optional set of context-specific keywords
            
        Returns:
            List of URLScore objects sorted by priority (highest first)
        """
        url_scores = []
        
        for url in urls:
            score = self._score_url(url, context_keywords)
            url_scores.append(score)
        
        # Sort by priority score (descending)
        url_scores.sort(key=lambda x: x.priority_score, reverse=True)
        
        self.logger.info(f"Prioritized {len(urls)} URLs, top score: {url_scores[0].priority_score:.2f}")
        
        return url_scores
    
    def _score_url(self, url: str, context_keywords: Optional[Set[str]] = None) -> URLScore:
        """
        Score a single URL for relevance and quality
        
        Args:
            url: URL to score
            context_keywords: Optional context keywords
            
        Returns:
            URLScore object
        """
        reasoning = []
        
        # Parse URL components
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        query = parsed.query.lower()
        
        # Calculate relevance score (0-10)
        relevance_score = self._calculate_relevance_score(
            url, domain, path, query, context_keywords, reasoning
        )
        
        # Calculate quality score (0-10)
        quality_score = self._calculate_quality_score(
            url, domain, path, reasoning
        )
        
        # Calculate combined priority score
        priority_score = (relevance_score * 0.6) + (quality_score * 0.4)
        
        # Determine category
        category = self._categorize_url(url, domain, path)
        
        return URLScore(
            url=url,
            relevance_score=relevance_score,
            quality_score=quality_score,
            priority_score=priority_score,
            reasoning=reasoning,
            category=category
        )
    
    def _calculate_relevance_score(self, url: str, domain: str, path: str, 
                                 query: str, context_keywords: Optional[Set[str]], 
                                 reasoning: List[str]) -> float:
        """Calculate relevance score based on grant-specific indicators"""
        score = 0.0
        
        # Check for high-priority grant keywords
        full_url = url.lower()
        grant_keyword_matches = sum(1 for kw in self.high_priority_keywords 
                                  if kw in full_url)
        if grant_keyword_matches > 0:
            boost = min(grant_keyword_matches * 1.5, 4.0)
            score += boost
            reasoning.append(f"Grant keywords (+{boost:.1f}): {grant_keyword_matches} matches")
        
        # Check for education-specific keywords
        edu_matches = sum(1 for kw in self.education_keywords if kw in full_url)
        if edu_matches > 0:
            boost = min(edu_matches * 1.0, 2.0)
            score += boost
            reasoning.append(f"Education keywords (+{boost:.1f}): {edu_matches} matches")
        
        # Check for AI/technology keywords
        ai_matches = sum(1 for kw in self.ai_keywords if kw in full_url)
        if ai_matches > 0:
            boost = min(ai_matches * 0.8, 1.5)
            score += boost
            reasoning.append(f"AI/tech keywords (+{boost:.1f}): {ai_matches} matches")
        
        # Check for context keywords if provided
        if context_keywords:
            context_matches = sum(1 for kw in context_keywords if kw.lower() in full_url)
            if context_matches > 0:
                boost = min(context_matches * 1.2, 2.5)
                score += boost
                reasoning.append(f"Context keywords (+{boost:.1f}): {context_matches} matches")
        
        # Check for high-value indicators
        value_matches = sum(1 for pattern in self.high_value_indicators 
                           if re.search(pattern, url, re.IGNORECASE))
        if value_matches > 0:
            boost = min(value_matches * 1.5, 3.0)
            score += boost
            reasoning.append(f"High-value indicators (+{boost:.1f}): {value_matches} matches")
        
        # Check for urgency indicators
        urgency_matches = sum(1 for pattern in self.urgency_indicators 
                             if re.search(pattern, url, re.IGNORECASE))
        if urgency_matches > 0:
            boost = min(urgency_matches * 1.0, 2.0)
            score += boost
            reasoning.append(f"Urgency indicators (+{boost:.1f}): {urgency_matches} matches")
        
        # Path-based relevance
        quality_path_matches = sum(1 for pattern in self.quality_url_patterns 
                                  if re.search(pattern, path))
        if quality_path_matches > 0:
            boost = min(quality_path_matches * 1.2, 2.5)
            score += boost
            reasoning.append(f"Quality URL patterns (+{boost:.1f}): {quality_path_matches} matches")
        
        return min(score, 10.0)  # Cap at 10
    
    def _calculate_quality_score(self, url: str, domain: str, path: str, 
                               reasoning: List[str]) -> float:
        """Calculate quality score based on domain authority and URL structure"""
        score = 0.0
        
        # Domain trust score
        domain_base = domain.replace('www.', '')
        if domain_base in self.trusted_domains:
            boost = self.trusted_domains[domain_base]
            score += boost
            reasoning.append(f"Trusted domain (+{boost:.1f}): {domain_base}")
        else:
            # Check for domain patterns that indicate quality
            if domain.endswith('.gov'):
                boost = 8.0
                score += boost
                reasoning.append(f"Government domain (+{boost:.1f})")
            elif domain.endswith('.edu'):
                boost = 6.0
                score += boost
                reasoning.append(f"Educational domain (+{boost:.1f})")
            elif domain.endswith('.org'):
                boost = 4.0
                score += boost
                reasoning.append(f"Nonprofit domain (+{boost:.1f})")
            elif any(term in domain for term in ['foundation', 'fund', 'institute']):
                boost = 5.0
                score += boost
                reasoning.append(f"Foundation/institute domain (+{boost:.1f})")
            else:
                boost = 2.0
                score += boost
                reasoning.append(f"General domain (+{boost:.1f})")
        
        # URL structure quality
        path_segments = [seg for seg in path.split('/') if seg]
        if len(path_segments) >= 2:
            boost = min(len(path_segments) * 0.3, 1.5)
            score += boost
            reasoning.append(f"URL depth (+{boost:.1f}): {len(path_segments)} segments")
        
        # Check for specific quality indicators in path
        if any(indicator in path for indicator in ['/2024/', '/2025/', 'current', 'active']):
            boost = 1.0
            score += boost
            reasoning.append(f"Current/recent content (+{boost:.1f})")
        
        return min(score, 10.0)  # Cap at 10
    
    def _categorize_url(self, url: str, domain: str, path: str) -> str:
        """Categorize the URL based on its characteristics"""
        full_url = url.lower()
        
        if domain.endswith('.gov'):
            return 'government'
        elif 'foundation' in domain or domain.endswith('.org'):
            return 'foundation'
        elif domain.endswith('.edu'):
            return 'academic'
        elif any(term in full_url for term in ['grants.', 'funding', 'pivot']):
            return 'grant_database'
        elif any(term in full_url for term in self.high_priority_keywords):
            return 'grant_opportunity'
        elif any(term in full_url for term in ['research', 'institute', 'center']):
            return 'research_institution'
        else:
            return 'general'
    
    def filter_by_category(self, url_scores: List[URLScore], 
                          categories: List[str]) -> List[URLScore]:
        """
        Filter URL scores by category
        
        Args:
            url_scores: List of URLScore objects
            categories: List of categories to include
            
        Returns:
            Filtered list of URLScore objects
        """
        filtered = [score for score in url_scores if score.category in categories]
        self.logger.info(f"Filtered {len(url_scores)} URLs to {len(filtered)} in categories: {categories}")
        return filtered
    
    def get_top_urls(self, url_scores: List[URLScore], limit: int = 20) -> List[str]:
        """
        Get top N URLs by priority score
        
        Args:
            url_scores: List of URLScore objects
            limit: Maximum number of URLs to return
            
        Returns:
            List of top-priority URLs
        """
        top_scores = url_scores[:limit]
        urls = [score.url for score in top_scores]
        
        if top_scores:
            self.logger.info(f"Selected top {len(urls)} URLs, score range: {top_scores[-1].priority_score:.2f} - {top_scores[0].priority_score:.2f}")
        
        return urls
    
    def print_url_analysis(self, url_scores: List[URLScore], limit: int = 10):
        """Print detailed analysis of top URLs"""
        print(f"\n🎯 Top {limit} URL Analysis:")
        print("=" * 80)
        
        for i, score in enumerate(url_scores[:limit], 1):
            print(f"\n{i}. {score.url}")
            print(f"   Priority: {score.priority_score:.2f} (Relevance: {score.relevance_score:.2f}, Quality: {score.quality_score:.2f})")
            print(f"   Category: {score.category}")
            if score.reasoning:
                print(f"   Reasoning: {'; '.join(score.reasoning[:3])}")  # Show top 3 reasons


def main():
    """Test the URL prioritizer"""
    # Test URLs
    test_urls = [
        'https://www.nsf.gov/funding/education/',
        'https://chanzuckerberg.com/science/programs/artificial-intelligence/',
        'https://www.templeton.org/grant-opportunities/',
        'https://example.com/general-page',
        'https://www.simonsfoundation.org/funding-opportunities/mathematics-physical-sciences/',
        'https://www.gatesfoundation.org/how-we-work/general-information/grant-opportunities',
        'https://grants.gov/search-grants.html?cfda=84.116',
        'https://www.fordfoundation.org/work/challenging-inequality/education-creativity-free-expression/',
        'https://blog.example.com/random-post',
        'https://harvard.edu/research/funding-opportunities'
    ]
    
    # Context keywords for testing
    context_keywords = {'leadership', 'artificial-intelligence', 'education', 'transformation'}
    
    prioritizer = URLPrioritizer()
    
    print("Testing URL Prioritization System")
    print(f"Analyzing {len(test_urls)} URLs with context: {context_keywords}")
    
    # Prioritize URLs
    url_scores = prioritizer.prioritize_urls(test_urls, context_keywords)
    
    # Print analysis
    prioritizer.print_url_analysis(url_scores)
    
    # Test filtering by category
    print("\n🏛️ Government URLs:")
    gov_urls = prioritizer.filter_by_category(url_scores, ['government'])
    for score in gov_urls:
        print(f"   {score.url} (score: {score.priority_score:.2f})")
    
    print("\n🏢 Foundation URLs:")
    foundation_urls = prioritizer.filter_by_category(url_scores, ['foundation'])
    for score in foundation_urls:
        print(f"   {score.url} (score: {score.priority_score:.2f})")
    
    # Get top URLs for scraping
    top_urls = prioritizer.get_top_urls(url_scores, limit=5)
    print(f"\n⭐ Top 5 URLs for scraping:")
    for i, url in enumerate(top_urls, 1):
        print(f"   {i}. {url}")


if __name__ == "__main__":
    main()