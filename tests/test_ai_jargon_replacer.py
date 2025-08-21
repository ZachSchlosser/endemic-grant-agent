#!/usr/bin/env python3
"""
Unit tests for ai_jargon_replacer.py
Tests pattern replacement, em dash handling, and style analysis
"""

import pytest
import sys
import os
import tempfile
import json
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_jargon_replacer import AIJargonReplacer, StyleProfile, JargonMatch


class TestAIJargonReplacer:
    """Test AI Jargon Replacer functionality"""
    
    @pytest.fixture
    def sample_config(self):
        """Create a sample configuration for testing"""
        config = {
            "overused_phrases": {
                "leverage": ["use", "utilize", "apply"],
                "groundbreaking": ["new", "novel", "first"],
                "paradigm": ["model", "framework", "approach"]
            },
            "typography_rules": {
                "em_dash_patterns": {
                    "definition_patterns": [
                        {
                            "pattern": "OntoEdit AI[\"']?\\s*[—,]\\s*the first tool that",
                            "replacement": "OntoEdit AI. The first tool that",
                            "description": "Dramatic pause with period"
                        }
                    ],
                    "hyphenation_fixes": [
                        {"from": "co — founder", "to": "co-founder"}
                    ]
                }
            },
            "em_dash_threshold": 2
        }
        return config
    
    @pytest.fixture
    def temp_config_file(self, sample_config):
        """Create a temporary config file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_config, f, indent=2)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        os.unlink(temp_path)
    
    def test_initialization(self, temp_config_file):
        replacer = AIJargonReplacer(temp_config_file)
        assert replacer.config is not None
        assert "overused_phrases" in replacer.config
        assert replacer.em_dash_threshold == 2
    
    def test_overused_phrase_detection(self, temp_config_file):
        replacer = AIJargonReplacer(temp_config_file)
        text = "We will leverage this groundbreaking paradigm to create solutions."
        
        result, matches = replacer.analyze_text(text)
        
        # Should find matches for leverage, groundbreaking, paradigm
        assert len(matches) >= 3
        match_words = [m.original for m in matches]
        assert any("leverage" in word.lower() for word in match_words)
        assert any("groundbreaking" in word.lower() for word in match_words)
        assert any("paradigm" in word.lower() for word in match_words)
    
    def test_em_dash_definition_patterns(self, temp_config_file):
        replacer = AIJargonReplacer(temp_config_file)
        text = "OntoEdit AI — the first tool that identifies cognitive patterns."
        
        result, matches = replacer.analyze_text(text)
        
        # Should find the definition pattern match
        definition_matches = [m for m in matches if 'definition_pattern' in m.category]
        assert len(definition_matches) > 0
        
        # Check that replacement was made
        assert "OntoEdit AI. The first tool that" in result
        assert "OntoEdit AI —" not in result
    
    def test_hyphenation_fixes(self, temp_config_file):
        replacer = AIJargonReplacer(temp_config_file)
        text = "The co — founder created this project."
        
        result, matches = replacer.analyze_text(text)
        
        # Should find hyphenation fix
        hyphen_matches = [m for m in matches if m.category == 'hyphenation_fix']
        assert len(hyphen_matches) > 0
        
        # Check that replacement was made
        assert "co-founder" in result
        assert "co — founder" not in result
    
    def test_em_dash_threshold_enforcement(self, temp_config_file):
        replacer = AIJargonReplacer(temp_config_file)
        # Text with excessive em dashes (more than threshold of 2)
        text = "This project — with multiple phases — and complex requirements — needs attention."
        
        result, matches = replacer.analyze_text(text)
        
        # Should find em dash reduction matches
        em_dash_matches = [m for m in matches if 'em_dash_reduction' in m.category]
        assert len(em_dash_matches) > 0
        
        # Result should have fewer em dashes
        original_count = text.count('—')
        result_count = result.count('—')
        assert result_count < original_count
    
    def test_style_profile_analysis(self, temp_config_file):
        replacer = AIJargonReplacer(temp_config_file)
        text = "This is a comprehensive analysis of the innovative approach. Furthermore, we will leverage cutting-edge methodologies."
        
        style_profile = replacer.analyze_style(text)
        
        assert isinstance(style_profile, StyleProfile)
        assert style_profile.avg_sentence_length > 0
        assert style_profile.formal_words_ratio >= 0
        assert style_profile.em_dash_frequency >= 0
        assert len(style_profile.common_words) > 0
    
    def test_no_changes_needed(self, temp_config_file):
        replacer = AIJargonReplacer(temp_config_file)
        text = "This is simple, clear text with no jargon or issues."
        
        result, matches = replacer.analyze_text(text)
        
        assert len(matches) == 0 or all(m.confidence < 0.5 for m in matches)
        # Text should be mostly unchanged (might have minor formatting)
        assert "simple, clear text" in result


class TestJargonMatch:
    """Test JargonMatch data structure"""
    
    def test_jargon_match_creation(self):
        match = JargonMatch(
            original="leverage",
            replacement="use",
            start_pos=10,
            end_pos=18,
            category="overused_phrase",
            confidence=0.8
        )
        
        assert match.original == "leverage"
        assert match.replacement == "use"
        assert match.start_pos == 10
        assert match.end_pos == 18
        assert match.category == "overused_phrase"
        assert match.confidence == 0.8


class TestStyleProfile:
    """Test StyleProfile analysis"""
    
    def test_style_profile_creation(self):
        common_words = {"the", "and", "of", "in"}
        tone_indicators = {"formal": 5, "casual": 2}
        
        profile = StyleProfile(
            avg_sentence_length=15.5,
            formal_words_ratio=0.3,
            transition_words_ratio=0.1,
            em_dash_frequency=0.05,
            common_words=common_words,
            tone_indicators=tone_indicators
        )
        
        assert profile.avg_sentence_length == 15.5
        assert profile.formal_words_ratio == 0.3
        assert profile.transition_words_ratio == 0.1
        assert profile.em_dash_frequency == 0.05
        assert profile.common_words == common_words
        assert profile.tone_indicators == tone_indicators


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_missing_config_file(self):
        # Should not crash with missing config file
        replacer = AIJargonReplacer("nonexistent_file.json")
        text = "Test text"
        result, matches = replacer.analyze_text(text)
        
        # Should return something reasonable
        assert isinstance(result, str)
        assert isinstance(matches, list)
    
    def test_malformed_config(self):
        # Create malformed config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": json}')  # Invalid JSON
            temp_path = f.name
        
        try:
            replacer = AIJargonReplacer(temp_path)
            text = "Test text"
            result, matches = replacer.analyze_text(text)
            
            # Should handle gracefully
            assert isinstance(result, str)
            assert isinstance(matches, list)
        finally:
            os.unlink(temp_path)
    
    def test_empty_text(self, temp_config_file):
        replacer = AIJargonReplacer(temp_config_file)
        result, matches = replacer.analyze_text("")
        
        assert result == ""
        assert len(matches) == 0
    
    def test_unicode_handling(self, temp_config_file):
        replacer = AIJargonReplacer(temp_config_file)
        text = "This leverages ñäme and café for résumé purposes."
        
        result, matches = replacer.analyze_text(text)
        
        # Should handle unicode properly
        assert "ñäme" in result
        assert "café" in result
        assert "résumé" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])