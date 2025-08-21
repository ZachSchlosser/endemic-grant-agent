# AI Jargon Replacement Hook System

A comprehensive system for detecting and replacing common AI writing patterns to make grant proposals and other documents sound more natural and compelling.

## Overview

The AI Jargon Replacer is designed specifically for the Endemic Grant Agent to ensure that funding proposals avoid the telltale signs of AI-generated text. It detects overused phrases, excessive formal transitions, buzzword clustering, and other patterns that make writing sound artificial.

## Features

### 🎯 **Pattern Detection**
- **Overused Phrases**: Detects 50+ common AI phrases like "delve into", "groundbreaking", "leverage"
- **Em Dash Overuse**: Identifies excessive use of em dashes (more than 2 per page)
- **Formal Transitions**: Catches overly formal connectors like "furthermore", "moreover"
- **Buzzword Clustering**: Detects multiple buzzwords in close proximity

### 🎨 **Style Analysis**
- **Reference Document Matching**: Analyzes target documents to match writing style
- **Context-Aware Replacements**: Chooses replacements based on surrounding text
- **Tone Detection**: Identifies academic, business, or casual writing contexts
- **Sentence Length Analysis**: Tracks and adjusts average sentence lengths

### ⚙️ **Smart Replacements**
- **Contextual Selection**: Picks the best replacement based on context
- **Domain-Specific Alternatives**: Different replacements for academic vs. business contexts
- **Confidence Scoring**: Each replacement includes a confidence score
- **Preservation of Meaning**: Maintains the original intent while improving naturalness

## Installation & Setup

### Requirements
The system requires Python 3.6+ and the following packages:
```bash
pip install requests
```

### Configuration
The system uses `jargon_config.json` for all pattern definitions and replacement rules. This file contains:
- Overused phrases and their alternatives
- Buzzword clusters to detect
- Context-specific replacement priorities
- Style matching parameters

### Claude Integration
The system automatically integrates with Claude Code through post-processing hooks in `settings.json`. It processes files after Write and MultiEdit operations.

## Usage

### Command Line Interface

#### Basic Usage
```bash
# Analyze and clean a file
python3 ai_jargon_replacer.py proposal.txt

# Analyze text directly
python3 ai_jargon_replacer.py --text "This groundbreaking approach will leverage innovative solutions"

# Use custom configuration
python3 ai_jargon_replacer.py proposal.txt --config custom_config.json
```

#### Advanced Options
```bash
# Match style to reference document
python3 ai_jargon_replacer.py proposal.txt --reference style_guide.txt

# Save cleaned version to new file
python3 ai_jargon_replacer.py proposal.txt --output cleaned_proposal.txt

# Generate detailed report
python3 ai_jargon_replacer.py proposal.txt --report

# Quiet mode (only errors)
python3 ai_jargon_replacer.py proposal.txt --quiet
```

### Python API

```python
from ai_jargon_replacer import AIJargonReplacer

# Initialize with default config
replacer = AIJargonReplacer("jargon_config.json")

# Analyze text
text = "This groundbreaking research will delve into innovative approaches..."
cleaned_text, matches = replacer.analyze_text(text)

# Generate report
report = replacer.generate_report(matches)
print(report)

# Style analysis
style_profile = replacer.analyze_style(text)
print(f"Average sentence length: {style_profile.avg_sentence_length}")
```

### Reference Document Analysis

```python
# Analyze a reference document for style matching
reference_style = replacer.analyze_reference_document("reference.txt")

# Or from a URL
reference_style = replacer.analyze_reference_document("https://example.com/style-guide")

# Apply style matching
cleaned_text, matches = replacer.analyze_text(original_text, reference_style)
```

## Configuration Details

### Overused Phrases
The system detects and replaces common AI phrases:

```json
{
  "overused_phrases": {
    "delve into": ["explore", "examine", "look at", "investigate"],
    "groundbreaking": ["new", "novel", "first", "pioneering"],
    "leverage": ["use", "utilize", "apply", "employ"]
  }
}
```

### Context-Aware Replacements
Different contexts get different replacement priorities:

```json
{
  "replacement_priorities": {
    "grant_writing": {
      "transformative": ["meaningful", "significant", "impactful"],
      "innovative": ["creative", "original", "new"]
    },
    "academic": {
      "delve into": ["examine", "investigate", "analyze"]
    },
    "business": {
      "leverage": ["utilize", "use", "employ"]
    }
  }
}
```

### Buzzword Clusters
Identifies related buzzwords that shouldn't appear together:

```json
{
  "buzzword_clusters": [
    ["innovative", "groundbreaking", "revolutionary", "cutting-edge"],
    ["leverage", "utilize", "optimize", "streamline"],
    ["seamless", "integrated", "comprehensive", "holistic"]
  ]
}
```

## Examples

### Before and After

**Before (AI-Generated Style):**
> This groundbreaking proposal delves into innovative methodologies to leverage cutting-edge research. Furthermore, our comprehensive framework will optimize transformative outcomes through seamless integration of best practices. The paradigm shift we propose will be revolutionary for the field.

**After (Natural Style):**
> This pioneering proposal examines creative methods to apply advanced research. Also, our complete framework will improve meaningful outcomes through smooth integration of proven techniques. The major change we propose will be significant for the field.

### Report Output

```
AI JARGON ANALYSIS REPORT
==============================

OVERUSED PHRASE (8 issues)
----------------------------------------
• 'groundbreaking' → 'pioneering' (confidence: 0.9)
• 'delves into' → 'examines' (confidence: 0.9)
• 'innovative' → 'creative' (confidence: 0.9)
• 'leverage' → 'apply' (confidence: 0.9)
• 'cutting-edge' → 'advanced' (confidence: 0.9)
• 'comprehensive' → 'complete' (confidence: 0.9)
• 'optimize' → 'improve' (confidence: 0.9)
• 'transformative' → 'meaningful' (confidence: 0.9)

FORMAL TRANSITION (1 issues)
----------------------------------------
• 'Furthermore' → 'Also' (confidence: 0.8)

BUZZWORD CLUSTER (2 issues)
----------------------------------------
• 'seamless' → 'smooth' (confidence: 0.6)
• 'paradigm shift' → 'major change' (confidence: 0.6)

TOTAL CHANGES: 11
```

## Testing

Run the test suite to verify functionality:

```bash
python3 test_jargon_replacer.py
```

The test suite covers:
- Overused phrase detection
- Em dash pattern analysis
- Buzzword clustering
- Style analysis
- Command-line interface
- Grant proposal specific patterns

## Integration with Endemic Grant Agent

### Automatic Processing
The system automatically processes files when you use Write or MultiEdit operations in Claude Code. The hook system:

1. Runs the proposal validator first
2. Applies jargon replacement
3. Provides feedback on changes made
4. Preserves the original file structure

### Claude Settings Integration
The system is integrated through `/Users/home/.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "cd '/Users/home/Desktop/Endemic Grant Agent' && python3 ai_jargon_replacer.py '$FILE_PATH' --config jargon_config.json --output '$FILE_PATH.cleaned' --report --quiet 2>/dev/null && if [ -f '$FILE_PATH.cleaned' ]; then mv '$FILE_PATH.cleaned' '$FILE_PATH' && echo 'AI JARGON REPLACER: Processed for natural language patterns'; fi"
          }
        ]
      }
    ]
  }
}
```

### Workflow Integration
For grant proposals, the recommended workflow is:

1. **Write Initial Draft**: Use Claude to generate the initial proposal content
2. **Automatic Processing**: The jargon replacer automatically processes the output
3. **Review Changes**: Check the generated report for improvements made
4. **Style Matching**: Optionally provide a reference document for style consistency
5. **Final Review**: Review the cleaned text to ensure it maintains the intended meaning

## Customization

### Adding New Patterns
To add new jargon patterns, edit `jargon_config.json`:

```json
{
  "overused_phrases": {
    "your_new_phrase": ["replacement1", "replacement2", "replacement3"]
  }
}
```

### Context-Specific Rules
Add domain-specific replacement rules:

```json
{
  "replacement_priorities": {
    "your_domain": {
      "phrase": ["domain_specific_replacement"]
    }
  }
}
```

### Custom Configurations
Create custom configuration files for different use cases:

```bash
# Use custom config
python3 ai_jargon_replacer.py proposal.txt --config medical_research_config.json
```

## Best Practices

### For Grant Writing
1. **Run Analysis Early**: Process proposals during drafting, not just at the end
2. **Use Reference Documents**: Provide successful proposals as style references
3. **Review Replacements**: Always review suggested changes for context appropriateness
4. **Maintain Authenticity**: Ensure the final text still reflects your unique voice

### For Style Matching
1. **Choose Appropriate References**: Use documents from the same domain/funder type
2. **Consider Audience**: Match the formality level to your target audience
3. **Balance Consistency and Variety**: Avoid making all text sound identical

### For Configuration
1. **Regular Updates**: Update the jargon patterns based on new AI writing trends
2. **Domain Specificity**: Maintain separate configs for different writing domains
3. **Confidence Thresholds**: Adjust confidence levels based on your risk tolerance

## Troubleshooting

### Common Issues

**Issue: Script not running automatically**
- Check that the hook is properly configured in `settings.json`
- Verify the file path in the hook command
- Ensure Python 3 is available in the environment

**Issue: Too many false positives**
- Adjust confidence thresholds in the configuration
- Add domain-specific context rules
- Reduce the strictness of buzzword clustering

**Issue: Replacements don't fit context**
- Add more context clues to the configuration
- Use reference document style matching
- Manually review and adjust replacement priorities

**Issue: Reference document analysis fails**
- Check that the URL/file path is accessible
- Verify that the document contains enough text for analysis
- Ensure proper encoding for text files

### Performance Optimization

For large documents:
- Use the `--quiet` flag to reduce output
- Process sections separately if needed
- Consider increasing confidence thresholds to reduce processing time

### Debugging

Enable verbose output for debugging:
```bash
# Remove --quiet flag and add --report for full analysis
python3 ai_jargon_replacer.py proposal.txt --config jargon_config.json --report
```

## Contributing

To extend the system:

1. **Add New Patterns**: Update `jargon_config.json` with new detection patterns
2. **Improve Context Analysis**: Enhance the context-aware replacement logic
3. **Add New Categories**: Create new jargon categories beyond the current ones
4. **Enhance Style Matching**: Improve the reference document analysis algorithms

## License & Usage

This tool is specifically designed for The Divinity School at Endemic's grant writing needs. The configuration and patterns are optimized for educational and research funding proposals.

---

For questions or issues, refer to the main Endemic Grant Agent documentation or test the system using `test_jargon_replacer.py`.