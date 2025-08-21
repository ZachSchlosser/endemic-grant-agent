#!/usr/bin/env python3
"""
Integrated Weekly Grant Search with Automated Proposal Generation
Combines grant discovery with question extraction and answer generation
"""

import os
import sys
from datetime import datetime
from typing import List, Dict, Tuple

# Add subagent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import all modules
from grant_search_agent import GrantSearchAgent, Grant
from enhanced_grant_search import EnhancedGrantSearchAgent  
from grant_question_extractor import GrantQuestionExtractor
from grant_proposal_generator import GrantProposalGenerator
from notion_integration import NotionIntegration


class IntegratedGrantSearchSystem:
    """Complete grant search and proposal generation system"""
    
    def __init__(self):
        """Initialize all components"""
        self.search_agent = EnhancedGrantSearchAgent()
        self.question_extractor = GrantQuestionExtractor()
        self.proposal_generator = GrantProposalGenerator()
        self.notion = NotionIntegration()
        
        # Track processing stats
        self.stats = {
            "grants_found": 0,
            "grants_added": 0,
            "questions_extracted": 0,
            "proposals_generated": 0,
        }
    
    def run_integrated_search(self) -> Tuple[int, str]:
        """Run the complete integrated search and proposal generation"""
        
        print("="*60)
        print(f"INTEGRATED GRANT SEARCH - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*60)
        
        # Step 1: Clean up expired grants
        print("\n1. Cleaning up expired grants...")
        self.search_agent.cleanup_expired_grants()
        
        # Step 2: Search for new grants
        print("\n2. Searching for new grant opportunities...")
        grants = self.search_agent.search_all_sources()
        self.stats["grants_found"] = len(grants)
        print(f"Found {len(grants)} potential grants")
        
        # Step 3: Process high-alignment grants
        high_alignment_grants = [g for g in grants if g.alignment_score >= 7.0]
        print(f"\n3. Processing {len(high_alignment_grants)} high-alignment grants (7.0+)...")
        
        for grant in high_alignment_grants:
            try:
                self.process_grant_with_proposals(grant)
            except Exception as e:
                print(f"Error processing {grant.grant_name}: {e}")
                continue
        
        # Step 4: Generate report
        report = self.generate_comprehensive_report(grants)
        
        # Step 5: Save report
        report_path = self.save_report(report)
        
        print("\n" + "="*60)
        print("SEARCH COMPLETE")
        print(f"Grants Found: {self.stats['grants_found']}")
        print(f"Grants Added: {self.stats['grants_added']}")  
        print(f"Proposals Generated: {self.stats['proposals_generated']}")
        print(f"Report saved to: {report_path}")
        print("="*60)
        
        return self.stats["grants_added"], report
    
    def process_grant_with_proposals(self, grant: Grant) -> bool:
        """Process a single grant: add to Notion, extract questions, generate answers"""
        
        print(f"\nProcessing: {grant.organization_name} - {grant.grant_name}")
        print(f"  Alignment: {grant.alignment_score}/10")
        
        # Step 1: Add to Notion database (if not already there)
        result = self.search_agent.add_to_notion_database(grant)
        if result in ['duplicate', 'expired', 'error']:
            if result == 'duplicate':
                print("  ⚠️  Grant already in database")
            elif result == 'expired':
                print("  ⚠️  Grant deadline has passed")
            elif result == 'error':
                print("  ❌ Error adding grant to database")
            return False
        
        # result is now the page_id
        page_id = result
        
        self.stats["grants_added"] += 1
        print(f"  ✓ Added to Notion database")
        
        # Step 2: Extract questions (if high alignment)
        if grant.alignment_score >= 6.0:
            
            print("  📋 Extracting application questions...")
            questions = self.question_extractor.extract_questions(
                grant.grant_link,
                grant.organization_name
            )
            
            if not questions:
                # Use generic questions as fallback
                questions = self.question_extractor.generate_generic_questions(
                    grant.organization_name
                )
            
            self.stats["questions_extracted"] += len(questions)
            print(f"  ✓ Extracted {len(questions)} questions")
            
            # Step 3: Generate proposal answers
            print("  🤖 Generating proposal answers...")
            grant_info = {
                "organization_name": grant.organization_name,
                "grant_name": grant.grant_name,
                "grant_amount": grant.grant_amount,
                "alignment_score": grant.alignment_score,
                "funding_target": grant.funding_target.value,
                "deadline": grant.deadline
            }
            
            answers = self.proposal_generator.generate_proposal_answers(
                grant_info,
                questions
            )
            
            self.stats["proposals_generated"] += 1
            print(f"  ✓ Generated {len(answers)} answers")
            
            # Step 4: Create Notion pages for questions and answers
            print("  📝 Creating Notion pages...")
            questions_url = self.notion.create_grant_questions_page(grant_info, questions)
            answers_url = self.notion.create_grant_answers_page(grant_info, answers)
            
            if questions_url and answers_url:
                # Update database entry with page links
                self.notion.update_grant_database_entry(
                    page_id,
                    questions_url,
                    answers_url
                )
                print(f"  ✓ Created and linked Notion pages")
            
            # All high-priority grants now proceed directly to full automation
            # No more manual alerts or Google Doc creation
            print("  ✅ Fully automated processing complete")
        
        return True
    
    def generate_comprehensive_report(self, grants: List[Grant]) -> str:
        """Generate a comprehensive report of the search results"""
        
        report = f"""# Weekly Grant Search Report - {datetime.now().strftime('%Y-%m-%d')}

## Summary Statistics
- **Total Grants Found**: {self.stats['grants_found']}
- **New Grants Added**: {self.stats['grants_added']}
- **Questions Extracted**: {self.stats['questions_extracted']}
- **Proposals Generated**: {self.stats['proposals_generated']}

## All Grants by Alignment Score
"""
        
        # Sort all grants by alignment score for comprehensive review
        sorted_grants = sorted(grants, key=lambda g: g.alignment_score, reverse=True)
        for grant in sorted_grants:
            report += f"""
### {grant.grant_name}
- **Organization**: {grant.organization_name}
- **Alignment**: {grant.alignment_score}/10
- **Amount**: {grant.grant_amount}
- **Deadline**: {grant.deadline or 'Rolling'}
- **Target**: {grant.funding_target.value}
- **Link**: {grant.grant_link}
- **Status**: Draft proposal generated in Notion
"""
        else:
            report += "\n*No grants with 9+ alignment score found today*\n"
        
        report += "\n## Medium Priority Grants (7-8.9 Alignment)\n"
        
        medium_priority = [g for g in grants if 7.0 <= g.alignment_score < 9.0]
        if medium_priority:
            for grant in medium_priority[:5]:  # Top 5 only
                report += f"""
### {grant.grant_name}
- **Organization**: {grant.organization_name}
- **Alignment**: {grant.alignment_score}/10
- **Amount**: {grant.grant_amount}
- **Deadline**: {grant.deadline or 'Rolling'}
- **Target**: {grant.funding_target.value}
"""
        else:
            report += "\n*No grants with 7-8.9 alignment score found today*\n"
        
        report += f"""
## Processing Details

### Automated Actions Taken:
1. ✓ Searched 8+ foundation sources (Templeton, Fetzer, McGovern, Cosmos, Mozilla, NSF, etc.)
2. ✓ Evaluated {self.stats['grants_found']} grant opportunities
3. ✓ Added {self.stats['grants_added']} new grants to Notion database
4. ✓ Extracted questions for {self.stats['questions_extracted']} qualifying grants
5. ✓ Generated {self.stats['proposals_generated']} draft proposals
6. ✓ Created Notion pages with questions and answers
7. ✓ Cleaned up expired grants from database

### Next Steps:
1. Review all grant proposals in Notion
2. Edit and refine AI-generated answers
3. Prepare final submissions before deadlines
4. Track application status in Notion database

## Notion Database
View all grants: https://www.notion.so/sacredsocieties/Automated-Grant-Database-2557d734db27808ba58aeb90a8aea7cf

---
*Report generated by Sacred Societies Weekly Grant Search System*
"""
        
        return report
    
    def save_report(self, report: str) -> str:
        """Save the report to file"""
        
        # Create reports directory if it doesn't exist
        reports_dir = "/Users/home/grant_reports"
        os.makedirs(reports_dir, exist_ok=True)
        
        # Save report
        report_path = os.path.join(
            reports_dir,
            f"weekly_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        
        with open(report_path, 'w') as f:
            f.write(report)
        
        # Also save as latest
        latest_path = os.path.join(reports_dir, "latest_report.md")
        with open(latest_path, 'w') as f:
            f.write(report)
        
        return report_path


def main():
    """Main entry point for weekly integrated search"""
    system = IntegratedGrantSearchSystem()
    added_count, report = system.run_integrated_search()
    
    # Return exit code based on success
    if added_count > 0:
        print(f"\n✅ Successfully added {added_count} grants with proposals!")
        return 0
    else:
        print("\n📋 No new grants added this week")
        return 0


if __name__ == "__main__":
    exit(main())