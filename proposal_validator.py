#!/usr/bin/env python3
"""
Grant Proposal Validation Hook
Automatically validates and fixes character/word limits in grant proposals
"""

import re
import sys

# Common grant application limits
LIMITS = {
    'tweet': 140,  # Twitter/X character limit
    'short_description': 280,  # Double tweet
    'elevator_pitch': 100,  # Word limit for elevator pitches
    'abstract': 250,  # Word limit for abstracts
    'proposal_short': 500,  # Word limit for short proposals
    'proposal_medium': 1000,  # Word limit for medium proposals
    'proposal_long': 2000,  # Word limit for long proposals
}

def count_characters(text):
    """Count characters excluding leading/trailing whitespace"""
    return len(text.strip())

def count_words(text):
    """Count words in text"""
    return len(text.strip().split())

def truncate_to_char_limit(text, limit):
    """Truncate text to character limit, breaking at word boundaries when possible"""
    text = text.strip()
    if len(text) <= limit:
        return text
    
    # Try to break at word boundary
    truncated = text[:limit]
    last_space = truncated.rfind(' ')
    
    if last_space > limit * 0.8:  # If we can break at a word boundary without losing too much
        return truncated[:last_space].strip()
    else:
        return truncated.strip()

def truncate_to_word_limit(text, limit):
    """Truncate text to word limit"""
    words = text.strip().split()
    if len(words) <= limit:
        return text
    
    return ' '.join(words[:limit])

def validate_and_fix_proposal(content):
    """
    Validate proposal content and automatically fix limit violations
    Returns tuple: (fixed_content, violations_found)
    """
    violations = []
    fixed_content = content
    
    # Check for tweet descriptions (140 characters)
    tweet_pattern = r'(.*tweet.*<140.*?:)\s*(.*?)(?=\n\*\*|\n\n|\Z)'
    tweet_matches = re.finditer(tweet_pattern, content, re.IGNORECASE | re.DOTALL)
    
    for match in tweet_matches:
        label = match.group(1)
        tweet_text = match.group(2).strip()
        char_count = count_characters(tweet_text)
        
        if char_count > 140:
            violations.append(f"Tweet description: {char_count}/140 characters")
            fixed_tweet = truncate_to_char_limit(tweet_text, 140)
            fixed_content = fixed_content.replace(match.group(0), label + "\n" + fixed_tweet)
    
    # Check for short proposals (500 words)
    proposal_pattern = r'(.*<500 words.*?:)\s*(.*?)(?=\n\*\*|\n\n\*\*|\Z)'
    proposal_matches = re.finditer(proposal_pattern, content, re.IGNORECASE | re.DOTALL)
    
    for match in proposal_matches:
        label = match.group(1)
        proposal_text = match.group(2).strip()
        word_count = count_words(proposal_text)
        
        if word_count > 500:
            violations.append(f"Short proposal: {word_count}/500 words")
            fixed_proposal = truncate_to_word_limit(proposal_text, 500)
            fixed_content = fixed_content.replace(match.group(0), label + "\n\n" + fixed_proposal)
    
    # Check for other common patterns
    patterns = [
        (r'(.*1-2 sentences.*?:)\s*(.*?)(?=\n\*\*|\n\n|\Z)', 280, 'char'),  # 1-2 sentences
        (r'(.*elevator pitch.*?:)\s*(.*?)(?=\n\*\*|\n\n|\Z)', 100, 'word'),  # Elevator pitch
        (r'(.*abstract.*?:)\s*(.*?)(?=\n\*\*|\n\n|\Z)', 250, 'word'),  # Abstract
    ]
    
    for pattern, limit, limit_type in patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
        for match in matches:
            label = match.group(1)
            text = match.group(2).strip()
            
            if limit_type == 'char':
                count = count_characters(text)
                if count > limit:
                    violations.append(f"{label.strip()}: {count}/{limit} characters")
                    fixed_text = truncate_to_char_limit(text, limit)
                    fixed_content = fixed_content.replace(match.group(0), label + "\n" + fixed_text)
            else:  # word
                count = count_words(text)
                if count > limit:
                    violations.append(f"{label.strip()}: {count}/{limit} words")
                    fixed_text = truncate_to_word_limit(text, limit)
                    fixed_content = fixed_content.replace(match.group(0), label + "\n" + fixed_text)
    
    # Apply document balancing for multi-draft documents
    balanced_content, balance_violations = balance_document_sections(fixed_content)
    violations.extend(balance_violations)
    
    return balanced_content, violations

def balance_document_sections(text):
    """
    Balance em dashes across document sections (Draft 1, Draft 2, etc.)
    Integrated from final_balance.py functionality
    """
    violations = []
    processed_text = text
    
    # Check for draft sections
    if 'Draft ' in text:
        # Find all draft sections
        draft_sections = re.findall(r'(Draft \d+.*?)(?=Draft \d+|$)', text, re.DOTALL)
        
        for i, section in enumerate(draft_sections):
            draft_number = i + 1
            em_count = section.count('—')
            
            if em_count > 2:  # Max 2 em dashes per draft
                violations.append(f"Draft {draft_number}: {em_count}/2 em dashes (reducing excess)")
                
                # Apply specific reduction patterns for this draft
                reduced_section = reduce_em_dashes_in_section(section, 2)
                processed_text = processed_text.replace(section, reduced_section, 1)
    
    return processed_text, violations

def reduce_em_dashes_in_section(section_text, target_max=2):
    """
    Reduce em dashes in a specific section to target maximum
    Uses context-aware replacement strategies from final_balance.py
    """
    if section_text.count('—') <= target_max:
        return section_text
    
    processed_section = section_text
    
    # Apply specific patterns that were identified in final_balance.py
    replacements_to_make = [
        ('No compute needed — just pure philosophical', 'No compute needed: just pure philosophical'),
        ('Phase 01 is pure discovery — mapping cognitive', 'Phase 01 is pure discovery. Mapping cognitive'),
        ('pure discovery — mapping', 'pure discovery: mapping'),
        ('just pure philosophical — an AI', 'just pure philosophical. An AI'),
    ]
    
    for old_pattern, new_pattern in replacements_to_make:
        if old_pattern in processed_section:
            processed_section = processed_section.replace(old_pattern, new_pattern, 1)
            # Check if we've reached target
            if processed_section.count('—') <= target_max:
                break
    
    # If still over limit, apply general reduction
    current_count = processed_section.count('—')
    if current_count > target_max:
        # Find remaining em dashes and convert the least impactful ones
        em_matches = list(re.finditer(r'([^—\n]{10,50})\s*—\s*([^—\n]{10,50})', processed_section))
        
        # Sort by potential impact (shorter contexts = less impactful)
        em_matches.sort(key=lambda m: len(m.group(0)))
        
        for match in em_matches:
            if processed_section.count('—') <= target_max:
                break
                
            old_text = match.group(0)
            left_part = match.group(1).strip()
            right_part = match.group(2).strip()
            
            # Choose replacement intelligently
            if right_part and right_part[0].isupper():
                new_text = f"{left_part}. {right_part}"
            elif any(word in right_part.lower()[:15] for word in ['and', 'but', 'which', 'that']):
                new_text = f"{left_part}, {right_part}"
            else:
                new_text = f"{left_part}, {right_part}"
            
            processed_section = processed_section.replace(old_text, new_text, 1)
    
    return processed_section

def main():
    """Main function for command line usage"""
    if len(sys.argv) < 2:
        print("Usage: python3 proposal_validator.py <text_to_validate>")
        sys.exit(1)
    
    text = ' '.join(sys.argv[1:])
    fixed_text, violations = validate_and_fix_proposal(text)
    
    if violations:
        print("VIOLATIONS FOUND AND FIXED:")
        for violation in violations:
            print(f"- {violation}")
        print("\nFIXED TEXT:")
        print(fixed_text)
    else:
        print("No violations found.")
        print(text)

if __name__ == "__main__":
    main()