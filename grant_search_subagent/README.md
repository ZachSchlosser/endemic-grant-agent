# Grant Search Sub-Agent for Endemic Grant Agent

## Overview
This is an integrated grant search and proposal generation system that operates as a sub-agent of the Endemic Grant Agent. It automatically searches for grants, extracts application questions, generates draft proposals, and stores everything in Notion.

## Architecture
```
Endemic Grant Agent/
└── grant_search_subagent/
    ├── grant_search_agent.py          # Base grant search functionality
    ├── enhanced_grant_search.py       # Enhanced search with 8+ sources
    ├── grant_question_extractor.py    # Extracts questions from grant pages
    ├── grant_proposal_generator.py    # Generates proposals using AI
    ├── notion_integration.py          # Creates Notion pages and links
    └── integrated_weekly_search.py    # Main orchestration script
```

## Features

### 1. Grant Discovery
- Searches 8+ foundation sources including:
  - Cosmos Institute
  - Templeton Foundation
  - Mozilla Foundation
  - National Science Foundation
  - Mind & Life Institute
  - BIAL Foundation
  - Future of Humanity Institute
  - OpenAI Fund

### 2. Alignment Scoring
- Evaluates each grant on a 1-10 scale
- Considers Sacred Societies mission fit
- Boosts scores for consciousness/AI intersection
- Identifies high-priority opportunities (9+)

### 3. Question Extraction
- Scrapes grant application pages
- Parses PDF applications
- Identifies question types (essay, budget, timeline, etc.)
- Extracts word/character limits

### 4. Proposal Generation
- Uses Endemic Grant Agent's capabilities
- Applies AI jargon replacement
- Customizes tone for each funder
- Validates word counts

### 5. Notion Integration
- Creates database entries for each grant
- Generates separate pages for questions
- Generates separate pages for draft answers
- Links everything together
- Tracks application status

## Weekly Automation

### Schedule
Runs weekly on Monday at 9:00 AM via macOS launchd

### Script Location
`/Users/home/run_weekly_grant_search.sh`

### Service Name
`com.sacredsocieties.grantsearch`

### To Check Status
```bash
launchctl list | grep grantsearch
```

### To Run Manually
```bash
cd "/Users/home/Desktop/Endemic Grant Agent"
source venv/bin/activate
cd grant_search_subagent
python integrated_weekly_search.py
```

## Notion Database

### URL
https://www.notion.so/sacredsocieties/Automated-Grant-Database-2557d734db27808ba58aeb90a8aea7cf

### Fields
- Organization Name
- Grant Name
- Alignment Score (1-10)
- Grant Amount
- Deadline
- Grant Link
- Funding Target
- Status
- Grant Questions Page (link)
- Draft Answers Page (link)
- Notes
- Date Added

## Reports

Weekly reports are saved to:
- `/Users/home/grant_reports/weekly_report_YYYYMMDD_HHMMSS.md`
- `/Users/home/grant_reports/latest_report.md` (always current)

## Configuration

### API Keys
- **Notion API**: Set in environment or script
- **Anthropic API**: Uses system environment variable

### Virtual Environment
Uses Endemic Grant Agent's virtual environment at:
`/Users/home/Desktop/Endemic Grant Agent/venv/`

## Dependencies
- Python 3.x
- requests
- beautifulsoup4
- PyPDF2
- anthropic
- google-auth
- google-api-python-client

## Workflow

1. **Weekly Search** (Monday 9 AM)
   - Cleans up expired grants
   - Searches all foundation sources
   - Evaluates alignment scores

2. **High-Priority Processing** (7.0+ alignment)
   - Adds to Notion database
   - Extracts application questions
   - Generates draft proposals
   - Creates linked Notion pages

3. **Very High Priority** (9.0+ alignment)
   - Also creates Google Doc draft
   - Sends alert notification

4. **Report Generation**
   - Summarizes all findings
   - Highlights high-priority grants
   - Provides next steps

## Integration with Endemic Grant Agent

This sub-agent leverages the parent Endemic Grant Agent's:
- **auth.py**: Google API authentication
- **ai_jargon_replacer.py**: Natural language processing
- **proposal_validator.py**: Content validation
- **Google Docs integration**: Document creation

## Success Metrics

- Finds 5-15 relevant grants per search
- Generates proposals for grants with 8+ alignment
- Reduces proposal preparation from days to hours
- Never misses capturing application requirements
- Maintains 70%+ usability of AI drafts

## Troubleshooting

### If the weekly search doesn't run:
```bash
# Check launchd service
launchctl list | grep grantsearch

# Reload if needed
launchctl unload ~/Library/LaunchAgents/com.sacredsocieties.grantsearch.plist
launchctl load ~/Library/LaunchAgents/com.sacredsocieties.grantsearch.plist
```

### If imports fail:
```bash
# Activate virtual environment
cd "/Users/home/Desktop/Endemic Grant Agent"
source venv/bin/activate

# Install missing dependencies
pip install requests beautifulsoup4 PyPDF2 anthropic
```

### Check logs:
```bash
# View latest report
cat /Users/home/grant_reports/latest_report.md

# Check launchd logs
tail -f /Users/home/grant_reports/launchd_stdout.log
tail -f /Users/home/grant_reports/launchd_stderr.log
```

## Future Enhancements

- [ ] Add more foundation sources
- [ ] Implement grant deadline reminders
- [ ] Track application submissions
- [ ] Generate foundation-specific cover letters
- [ ] Add success rate tracking
- [ ] Implement collaborative review workflow

---

**Created**: August 20, 2025
**Status**: Production Ready
**Parent Project**: Endemic Grant Agent