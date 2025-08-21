#!/usr/bin/env python3
"""
Unit tests for proposal_validator.py
Tests word/character limits and document balancing functionality
"""

import pytest
import sys
import os
from unittest.mock import patch

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from proposal_validator import (
    count_characters, count_words, truncate_to_char_limit, 
    truncate_to_word_limit, validate_and_fix_proposal,
    balance_document_sections, reduce_em_dashes_in_section
)


class TestBasicFunctions:
    """Test basic utility functions"""
    
    def test_count_characters(self):
        assert count_characters("hello world") == 11
        assert count_characters("  hello world  ") == 11  # Strips whitespace
        assert count_characters("") == 0
        assert count_characters("   ") == 0
    
    def test_count_words(self):
        assert count_words("hello world") == 2
        assert count_words("  hello   world  ") == 2  # Handles extra spaces
        assert count_words("") == 0
        assert count_words("   ") == 0
        assert count_words("single") == 1
    
    def test_truncate_to_char_limit(self):
        text = "This is a test sentence that is longer than expected"
        result = truncate_to_char_limit(text, 20)
        assert len(result) <= 20
        assert result.endswith("test")  # Should break at word boundary
        
        # Test when text is already under limit
        short_text = "Short text"
        assert truncate_to_char_limit(short_text, 50) == short_text
    
    def test_truncate_to_word_limit(self):
        text = "One two three four five six seven eight"
        result = truncate_to_word_limit(text, 4)
        assert result == "One two three four"
        
        # Test when text is already under limit
        short_text = "One two"
        assert truncate_to_word_limit(short_text, 5) == short_text


class TestProposalValidation:
    """Test proposal validation and fixing"""
    
    def test_tweet_validation(self):
        # Create content with tweet that exceeds 140 characters
        long_tweet = "This is a very long tweet description that definitely exceeds the 140 character limit for Twitter posts and should be truncated by the validator"
        content = f"**Tweet description <140 characters:** {long_tweet}\n\n**Other content**"
        
        fixed_content, violations = validate_and_fix_proposal(content)
        
        assert len(violations) > 0
        assert "Tweet description" in violations[0]
        assert "140" in violations[0]
        # Ensure the fixed content has the tweet truncated
        assert len(long_tweet) > 140  # Original was too long
        tweet_in_fixed = fixed_content.split("**Other content**")[0]
        tweet_text = tweet_in_fixed.split(":**")[1].strip()
        assert len(tweet_text) <= 140
    
    def test_proposal_word_limit(self):
        # Create content with proposal that exceeds 500 words
        long_proposal = " ".join(["word"] * 600)  # 600 words
        content = f"**Proposal <500 words:** {long_proposal}\n\n**Other content**"
        
        fixed_content, violations = validate_and_fix_proposal(content)
        
        assert len(violations) > 0
        assert "500 words" in violations[0]
        # Check that proposal was truncated
        proposal_in_fixed = fixed_content.split("**Other content**")[0]
        proposal_text = proposal_in_fixed.split(":**")[1].strip()
        assert len(proposal_text.split()) <= 500
    
    def test_no_violations(self):
        content = "**Tweet <140 chars:** Short tweet\n**Proposal <500 words:** Short proposal"
        fixed_content, violations = validate_and_fix_proposal(content)
        
        assert len(violations) == 0
        assert fixed_content == content  # No changes needed


class TestDocumentBalancing:
    """Test document balancing functionality for multi-draft documents"""
    
    def test_balance_document_sections(self):
        content = """
Draft 1: This has — too many — em dashes — in one draft.

Draft 2: Another draft — with multiple — em dash — problems here.
"""
        balanced_content, violations = balance_document_sections(content)
        
        assert len(violations) == 2  # Both drafts should have violations
        assert "Draft 1" in violations[0] and "em dashes" in violations[0]
        assert "Draft 2" in violations[1] and "em dashes" in violations[1]
        
        # Count em dashes in result - should be reduced
        original_count = content.count('—')
        balanced_count = balanced_content.count('—')
        assert balanced_count < original_count
    
    def test_reduce_em_dashes_in_section(self):
        section = "This has — too many — em dashes — for good style."
        reduced = reduce_em_dashes_in_section(section, 2)
        
        assert reduced.count('—') <= 2
        # Should still be readable text
        assert "This has" in reduced
        assert "good style" in reduced
    
    def test_no_draft_sections(self):
        content = "Regular content with no draft sections."
        balanced_content, violations = balance_document_sections(content)
        
        assert len(violations) == 0
        assert balanced_content == content
    
    def test_acceptable_em_dash_count(self):
        content = """
Draft 1: This has — one em dash only.

Draft 2: This has — only one — em dash pair.
"""
        balanced_content, violations = balance_document_sections(content)
        
        assert len(violations) == 0  # Both drafts are within limit
        assert balanced_content == content  # No changes needed


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_empty_content(self):
        fixed_content, violations = validate_and_fix_proposal("")
        assert fixed_content == ""
        assert len(violations) == 0
    
    def test_malformed_patterns(self):
        content = "**Tweet <140:** No closing pattern"
        fixed_content, violations = validate_and_fix_proposal(content)
        # Should not crash, might not find pattern to fix
        assert isinstance(violations, list)
    
    def test_unicode_handling(self):
        content = "**Tweet <140 chars:** Unicode test: ñäme, café, résumé"
        fixed_content, violations = validate_and_fix_proposal(content)
        assert "ñäme" in fixed_content
        assert "café" in fixed_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])