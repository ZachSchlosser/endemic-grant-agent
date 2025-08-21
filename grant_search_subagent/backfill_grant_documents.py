#!/usr/bin/env python3
"""
Backfill Grant Documents Script
Generates question and answer documents for existing grants that lack them
"""

import os
import sys
import requests
from typing import List, Dict, Optional
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import required modules
from grant_search_agent import Grant, FundingTarget, GrantStatus
from grant_question_extractor import GrantQuestionExtractor
from grant_proposal_generator import GrantProposalGenerator
from notion_integration import NotionIntegration


class GrantDocumentBackfill:
    """Backfill question and answer documents for existing grants"""
    
    def __init__(self):
        """Initialize all components"""
        self.notion = NotionIntegration()
        self.question_extractor = GrantQuestionExtractor()
        self.proposal_generator = GrantProposalGenerator()
        
        print("Grant Document Backfill System Initialized")
        print("=" * 60)
    
    def get_grants_needing_backfill(self) -> List[Dict]:
        """Get all grants from database that lack question/answer documents"""
        
        print("🔍 Querying database for grants needing backfill...")
        
        url = f'https://api.notion.com/v1/databases/{self.notion.database_id}/query'
        
        try:
            response = requests.post(url, headers=self.notion.headers, json={})
            response.raise_for_status()
            
            results = response.json().get('results', [])
            grants_needing_backfill = []
            
            for grant_data in results:
                props = grant_data['properties']
                
                # Extract basic grant info
                org_name = props['Organization Name']['title'][0]['text']['content'] if props['Organization Name']['title'] else 'Unknown'
                grant_name = props['Grant Name']['rich_text'][0]['text']['content'] if props['Grant Name']['rich_text'] else 'Unknown'
                alignment_score = props['Alignment Score']['number'] if props['Alignment Score']['number'] else 0
                
                # Check if it has question/answer page links
                questions_link = props.get('Grant Questions Page', {}).get('url') if 'Grant Questions Page' in props else None
                answers_link = props.get('Draft Answers Page', {}).get('url') if 'Draft Answers Page' in props else None
                
                # Only process if missing documents and meets alignment threshold
                if (not questions_link or not answers_link) and alignment_score >= 6.0:
                    grant_info = {
                        'page_id': grant_data['id'],
                        'organization_name': org_name,
                        'grant_name': grant_name,
                        'alignment_score': alignment_score,
                        'grant_amount': props['Grant Amount']['rich_text'][0]['text']['content'] if props['Grant Amount']['rich_text'] else 'Unknown',
                        'grant_link': props['Grant Link']['url'] if props['Grant Link']['url'] else '',
                        'deadline': props.get('Deadline', {}).get('date', {}).get('start') if 'Deadline' in props else None,
                        'funding_target': props['Funding Target']['select']['name'] if props['Funding Target']['select'] else 'Divinity School Overall',
                        'notes': props['Notes']['rich_text'][0]['text']['content'] if props['Notes']['rich_text'] else '',
                        'has_questions': bool(questions_link),
                        'has_answers': bool(answers_link)
                    }
                    grants_needing_backfill.append(grant_info)
            
            print(f"✓ Found {len(grants_needing_backfill)} grants needing backfill")
            return grants_needing_backfill
            
        except Exception as e:
            print(f"❌ Error querying database: {e}")
            return []
    
    def convert_to_grant_object(self, grant_info: Dict) -> Grant:
        """Convert database grant info to Grant object"""
        
        # Map funding target string to enum
        funding_target_map = {
            'OntoEdit AI': FundingTarget.ONTOEDIT,
            'Securing the Nation\'s Future (SNF)': FundingTarget.SNF,
            'Divinity School Overall': FundingTarget.DIVINITY_SCHOOL
        }
        
        funding_target = funding_target_map.get(
            grant_info['funding_target'], 
            FundingTarget.DIVINITY_SCHOOL
        )
        
        return Grant(
            organization_name=grant_info['organization_name'],
            grant_name=grant_info['grant_name'],
            alignment_score=grant_info['alignment_score'],
            grant_amount=grant_info['grant_amount'],
            deadline=grant_info['deadline'],
            grant_link=grant_info['grant_link'],
            funding_target=funding_target,
            notes=grant_info['notes'],
            status=GrantStatus.NEW
        )
    
    def process_single_grant(self, grant_info: Dict) -> bool:
        """Process a single grant through the proposal generation pipeline"""
        
        print(f"\n📋 Processing: {grant_info['organization_name']} - {grant_info['grant_name']}")
        print(f"   Alignment: {grant_info['alignment_score']}/10")
        print(f"   Questions: {'✓' if grant_info['has_questions'] else '✗'}")
        print(f"   Answers: {'✓' if grant_info['has_answers'] else '✗'}")
        
        try:
            # Convert to Grant object
            grant = self.convert_to_grant_object(grant_info)
            
            # Step 1: Extract questions
            if not grant_info['has_questions']:
                print("   🔍 Extracting application questions...")
                questions = self.question_extractor.extract_questions(
                    grant.grant_link,
                    grant.organization_name
                )
                
                if not questions:
                    # Use generic questions as fallback
                    print("   📝 Using generic questions fallback...")
                    questions = self.question_extractor.generate_generic_questions(
                        grant.organization_name
                    )
                
                print(f"   ✓ Extracted {len(questions)} questions")
            else:
                print("   ⏭️  Questions already exist, skipping extraction")
                questions = []  # We'll generate generic ones for answer generation
            
            # Step 2: Generate answers (if needed)
            if not grant_info['has_answers'] and questions:
                print("   🤖 Generating proposal answers...")
                
                # Prepare grant info for proposal generation
                proposal_grant_info = {
                    "organization_name": grant.organization_name,
                    "grant_name": grant.grant_name,
                    "grant_amount": grant.grant_amount,
                    "alignment_score": grant.alignment_score,
                    "funding_target": grant.funding_target.value,
                    "deadline": grant.deadline
                }
                
                answers = self.proposal_generator.generate_proposal_answers(
                    proposal_grant_info,
                    questions
                )
                
                print(f"   ✓ Generated {len(answers)} answers")
            else:
                print("   ⏭️  Answers already exist or no questions available")
                answers = []
            
            # Step 3: Create Notion pages
            questions_url = None
            answers_url = None
            
            if not grant_info['has_questions'] and questions:
                print("   📄 Creating questions page...")
                grant_data = {
                    "organization_name": grant.organization_name,
                    "grant_name": grant.grant_name,
                    "grant_amount": grant.grant_amount,
                    "alignment_score": grant.alignment_score,
                    "funding_target": grant.funding_target.value,
                    "deadline": grant.deadline
                }
                questions_url = self.notion.create_grant_questions_page(grant_data, questions)
                
                if questions_url:
                    print("   ✓ Questions page created")
                else:
                    print("   ❌ Failed to create questions page")
            
            if not grant_info['has_answers'] and answers:
                print("   📄 Creating answers page...")
                grant_data = {
                    "organization_name": grant.organization_name,
                    "grant_name": grant.grant_name,
                    "grant_amount": grant.grant_amount,
                    "alignment_score": grant.alignment_score,
                    "funding_target": grant.funding_target.value,
                    "deadline": grant.deadline
                }
                answers_url = self.notion.create_grant_answers_page(grant_data, answers)
                
                if answers_url:
                    print("   ✓ Answers page created")
                else:
                    print("   ❌ Failed to create answers page")
            
            # Step 4: Update database entry with links
            if questions_url or answers_url:
                print("   🔗 Updating database links...")
                
                # Get current URLs from database
                current_questions_url = questions_url if questions_url else (grant_info.get('questions_url') or "")
                current_answers_url = answers_url if answers_url else (grant_info.get('answers_url') or "")
                
                if current_questions_url and current_answers_url:
                    success = self.notion.update_grant_database_entry(
                        grant_info['page_id'],
                        current_questions_url,
                        current_answers_url
                    )
                    
                    if success:
                        print("   ✓ Database updated with page links")
                    else:
                        print("   ⚠️  Database update failed")
                else:
                    print("   ⚠️  Missing URLs for database update")
            
            print(f"   ✅ {grant_info['grant_name']} processing complete")
            return True
            
        except Exception as e:
            print(f"   ❌ Error processing {grant_info['grant_name']}: {e}")
            return False
    
    def run_backfill(self) -> Dict[str, int]:
        """Run the complete backfill process"""
        
        print(f"🚀 Starting Grant Document Backfill - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # Get grants needing backfill
        grants = self.get_grants_needing_backfill()
        
        if not grants:
            print("✅ No grants need backfill - all documents are complete!")
            return {"processed": 0, "successful": 0, "failed": 0}
        
        # Process each grant
        stats = {"processed": 0, "successful": 0, "failed": 0}
        
        for grant in grants:
            stats["processed"] += 1
            if self.process_single_grant(grant):
                stats["successful"] += 1
            else:
                stats["failed"] += 1
        
        # Final summary
        print("\n" + "=" * 60)
        print("BACKFILL COMPLETE")
        print(f"Grants Processed: {stats['processed']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print("=" * 60)
        
        return stats


def main():
    """Main entry point for backfill script"""
    backfill = GrantDocumentBackfill()
    stats = backfill.run_backfill()
    
    # Return appropriate exit code
    if stats["failed"] == 0:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())