#!/usr/bin/env python3
"""
Sacred Societies Grant Search Agent
Automated daily grant discovery and evaluation system
Now integrated with Endemic Grant Agent for proposal generation
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import re
from dataclasses import dataclass
from enum import Enum

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configuration
NOTION_API_KEY = os.getenv('NOTION_API_KEY')
if not NOTION_API_KEY:
    raise ValueError("NOTION_API_KEY environment variable must be set")
DATABASE_ID = '2557d734-db27-813c-860a-eea78b88020e'
NOTION_VERSION = '2022-06-28'

# Headers for Notion API
NOTION_HEADERS = {
    'Authorization': f'Bearer {NOTION_API_KEY}',
    'Content-Type': 'application/json',
    'Notion-Version': NOTION_VERSION
}


class FundingTarget(Enum):
    DIVINITY_SCHOOL = "Divinity School Overall"
    ONTOEDIT = "OntoEdit AI"
    SNF = "Securing the Nation's Future (SNF)"
    FUTURES_WE_SHAPE = "The Futures We Must Shape"
    FOUR_POWERS = "Four Powers Framework"
    LEADERSHIP_PROGRAM = "Leadership Certificate Program"
    ORIGINALS = "Originals"


class GrantStatus(Enum):
    NEW = "New"
    REVIEWING = "Reviewing"
    APPLIED = "Applied"
    REJECTED = "Rejected"
    AWARDED = "Awarded"


@dataclass
class Grant:
    """Represents a grant opportunity"""
    organization_name: str
    grant_name: str
    alignment_score: float
    grant_amount: str
    deadline: Optional[str]
    grant_link: str
    funding_target: FundingTarget
    notes: str
    status: GrantStatus = GrantStatus.NEW
    date_added: str = None
    
    def __post_init__(self):
        if not self.date_added:
            self.date_added = datetime.now().strftime('%Y-%m-%d')


class GrantSearchAgent:
    """Main agent for searching and evaluating grants"""
    
    def __init__(self):
        self.database_id = DATABASE_ID
        self.keywords = [
            # Core concepts
            "consciousness", "artificial intelligence", "biological intelligence",
            "sacred technology", "spiritual innovation", "ontology", "epistemology",
            
            # Educational focus
            "alternative education", "nature-based learning", "transformative education",
            "holistic education", "contemplative education",
            
            # Research areas
            "AI ethics", "machine consciousness", "collective intelligence",
            "wisdom traditions", "indigenous knowledge", "complexity science",
            
            # Community and society
            "community transformation", "society design", "social innovation",
            "regenerative culture", "systems change"
        ]
        
        # Foundation targets with known alignment
        self.target_foundations = {
            "high_alignment": [
                "John Templeton Foundation",
                "Fetzer Institute", 
                "Cosmos Institute",
                "Patrick J. McGovern Foundation"
            ],
            "good_alignment": [
                "Mozilla Foundation",
                "RAAIS Foundation",
                "Long Term Future Fund",
                "Overbrook Foundation"
            ],
            "exploratory": [
                "Betty Moore Foundation",
                "Packard Foundation",
                "Louis Calder Foundation"
            ]
        }
    
    def evaluate_alignment(self, grant_description: str, foundation_name: str, 
                          grant_name: str, focus_areas: List[str]) -> Tuple[float, str]:
        """
        Evaluate grant alignment with Sacred Societies mission
        Returns: (alignment_score, reasoning)
        """
        score = 5.0  # Base score
        reasons = []
        
        # Check foundation alignment
        if foundation_name in self.target_foundations["high_alignment"]:
            score += 2.0
            reasons.append(f"{foundation_name} has high mission alignment")
        elif foundation_name in self.target_foundations["good_alignment"]:
            score += 1.0
            reasons.append(f"{foundation_name} has good mission alignment")
        
        # Check keyword matches in description
        description_lower = grant_description.lower()
        keyword_matches = 0
        matched_keywords = []
        
        for keyword in self.keywords:
            if keyword in description_lower:
                keyword_matches += 1
                matched_keywords.append(keyword)
        
        if keyword_matches >= 5:
            score += 2.0
            reasons.append(f"Strong keyword match: {', '.join(matched_keywords[:3])}...")
        elif keyword_matches >= 3:
            score += 1.5
            reasons.append(f"Good keyword match: {', '.join(matched_keywords)}")
        elif keyword_matches >= 1:
            score += 0.5
            reasons.append(f"Some keyword match: {', '.join(matched_keywords)}")
        
        # Check for specific high-value terms
        if "consciousness" in description_lower and "AI" in description_lower:
            score += 0.5
            reasons.append("Consciousness + AI focus")
        
        if "spiritual" in description_lower and "technology" in description_lower:
            score += 0.5
            reasons.append("Spiritual technology focus")
        
        # Cap score at 10
        score = min(score, 10.0)
        
        reasoning = "; ".join(reasons) if reasons else "General grant opportunity"
        return score, reasoning
    
    def determine_funding_target(self, grant_name: str, description: str) -> FundingTarget:
        """Determine which project/area this grant would fund"""
        name_lower = grant_name.lower()
        desc_lower = description.lower()
        combined = name_lower + " " + desc_lower
        
        # Check for OntoEdit specific keywords
        ontoedit_keywords = ["ontology", "knowledge graph", "semantic", "epistemology", 
                            "knowledge representation", "information architecture", "ontoedit"]
        for keyword in ontoedit_keywords:
            if keyword in combined:
                return FundingTarget.ONTOEDIT
        
        # Check for SNF (Securing the Nation's Future) keywords
        snf_keywords = ["national security", "ai safety", "securing", "nation", 
                       "ai literacy", "metacognitive", "human-ai collaboration"]
        for keyword in snf_keywords:
            if keyword in combined:
                return FundingTarget.SNF
        
        # Check for Futures We Must Shape keywords
        futures_keywords = ["futures", "executive briefing", "alignment briefing",
                          "investment strategy", "policy guidance", "strategic foresight"]
        for keyword in futures_keywords:
            if keyword in combined:
                return FundingTarget.FUTURES_WE_SHAPE
        
        # Check for Four Powers Framework keywords
        powers_keywords = ["visionary scholarship", "awakened perception", "crazy wisdom",
                         "passionate action", "four powers", "transformative leadership"]
        for keyword in powers_keywords:
            if keyword in combined:
                return FundingTarget.FOUR_POWERS
        
        # Check for Leadership Certificate Program keywords
        leadership_keywords = ["leadership certificate", "leadership program", "curriculum",
                            "educational program", "training program", "certificate program"]
        for keyword in leadership_keywords:
            if keyword in combined:
                return FundingTarget.LEADERSHIP_PROGRAM
        
        # Check for Originals keywords
        originals_keywords = ["podcast", "interview series", "cultural innovation", 
                            "community learning", "insight studio", "creative futures",
                            "biological intelligence", "watch party", "originality"]
        for keyword in originals_keywords:
            if keyword in combined:
                return FundingTarget.ORIGINALS
        
        # Default to overall funding
        return FundingTarget.DIVINITY_SCHOOL
    
    def search_templeton_foundation(self) -> List[Grant]:
        """Search John Templeton Foundation grants"""
        grants = []
        
        # Simulated grant data - in production, this would scrape or use API
        templeton_grants = [
            {
                "name": "Diverse Intelligences Grant",
                "description": "Supporting research on consciousness, AI, and non-human intelligence",
                "amount": "$100,000 - $500,000",
                "deadline": "2025-03-15",
                "link": "https://www.templetonworldcharity.org/our-priorities/discovery/diverse-intelligences"
            },
            {
                "name": "Science of Virtues",
                "description": "Research on wisdom, virtue, and human flourishing",
                "amount": "$50,000 - $250,000",
                "deadline": "2025-04-01",
                "link": "https://www.templeton.org/grants/science-of-virtues"
            }
        ]
        
        for grant_data in templeton_grants:
            alignment, notes = self.evaluate_alignment(
                grant_data["description"],
                "John Templeton Foundation",
                grant_data["name"],
                []
            )
            
            if alignment >= 5.0:  # Only add grants with minimum alignment
                grant = Grant(
                    organization_name="John Templeton Foundation",
                    grant_name=grant_data["name"],
                    alignment_score=alignment,
                    grant_amount=grant_data["amount"],
                    deadline=grant_data["deadline"],
                    grant_link=grant_data["link"],
                    funding_target=self.determine_funding_target(
                        grant_data["name"], 
                        grant_data["description"]
                    ),
                    notes=f"{grant_data['description']}. Alignment: {notes}"
                )
                grants.append(grant)
        
        return grants
    
    def search_fetzer_institute(self) -> List[Grant]:
        """Search Fetzer Institute grants"""
        grants = []
        
        fetzer_grants = [
            {
                "name": "Spiritual Innovation Grant",
                "description": "Supporting spiritual innovators building infrastructure for consciousness transformation",
                "amount": "$25,000 - $100,000",
                "deadline": "2025-02-28",
                "link": "https://fetzer.org/grants/spiritual-innovation"
            }
        ]
        
        for grant_data in fetzer_grants:
            alignment, notes = self.evaluate_alignment(
                grant_data["description"],
                "Fetzer Institute",
                grant_data["name"],
                []
            )
            
            if alignment >= 5.0:
                grant = Grant(
                    organization_name="Fetzer Institute",
                    grant_name=grant_data["name"],
                    alignment_score=alignment,
                    grant_amount=grant_data["amount"],
                    deadline=grant_data["deadline"],
                    grant_link=grant_data["link"],
                    funding_target=FundingTarget.DIVINITY_SCHOOL,
                    notes=f"{grant_data['description']}. Alignment: {notes}"
                )
                grants.append(grant)
        
        return grants
    
    def search_mcgovern_foundation(self) -> List[Grant]:
        """Search Patrick J. McGovern Foundation grants"""
        grants = []
        
        mcgovern_grants = [
            {
                "name": "AI and Society Grant",
                "description": "Advancing AI for human benefit with focus on consciousness and ethics",
                "amount": "$150,000 - $750,000",
                "deadline": "2025-05-01",
                "link": "https://www.mcgovern.org/grants/ai-society"
            }
        ]
        
        for grant_data in mcgovern_grants:
            alignment, notes = self.evaluate_alignment(
                grant_data["description"],
                "Patrick J. McGovern Foundation",
                grant_data["name"],
                []
            )
            
            if alignment >= 5.0:
                grant = Grant(
                    organization_name="Patrick J. McGovern Foundation",
                    grant_name=grant_data["name"],
                    alignment_score=alignment,
                    grant_amount=grant_data["amount"],
                    deadline=grant_data["deadline"],
                    grant_link=grant_data["link"],
                    funding_target=self.determine_funding_target(
                        grant_data["name"],
                        grant_data["description"]
                    ),
                    notes=f"{grant_data['description']}. Alignment: {notes}"
                )
                grants.append(grant)
        
        return grants
    
    def search_all_sources(self) -> List[Grant]:
        """Search all configured grant sources"""
        all_grants = []
        
        # Search each foundation
        all_grants.extend(self.search_templeton_foundation())
        all_grants.extend(self.search_fetzer_institute())
        all_grants.extend(self.search_mcgovern_foundation())
        
        # Sort by alignment score
        all_grants.sort(key=lambda x: x.alignment_score, reverse=True)
        
        return all_grants
    
    def add_to_notion_database(self, grant: Grant) -> str:
        """Add a grant to the Notion database
        Returns: page_id on success, 'expired', 'duplicate', or 'error'
        """
        # Check if already exists first
        if self.check_duplicate(grant):
            return 'duplicate'
        
        # Skip grants with past deadlines
        if grant.deadline:
            try:
                deadline_date = datetime.strptime(grant.deadline, '%Y-%m-%d')
                if deadline_date < datetime.now():
                    print(f"Skipping expired grant: {grant.grant_name} (Deadline: {grant.deadline})")
                    return 'expired'
            except ValueError as e:
                print(f"Warning: Could not parse deadline '{grant.deadline}' for {grant.grant_name}: {e}")
                # Continue with adding the grant if date parsing fails
        
        url = f'https://api.notion.com/v1/pages'
        
        # Prepare the data for Notion
        data = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Organization Name": {
                    "title": [{"text": {"content": grant.organization_name}}]
                },
                "Grant Name": {
                    "rich_text": [{"text": {"content": grant.grant_name}}]
                },
                "Alignment Score": {
                    "number": grant.alignment_score
                },
                "Grant Amount": {
                    "rich_text": [{"text": {"content": grant.grant_amount}}]
                },
                "Grant Link": {
                    "url": grant.grant_link
                },
                "Funding Target": {
                    "select": {"name": grant.funding_target.value}
                },
                "Status": {
                    "select": {"name": grant.status.value}
                },
                "Notes": {
                    "rich_text": [{"text": {"content": grant.notes}}]
                },
                "Date Added": {
                    "date": {"start": grant.date_added}
                }
            }
        }
        
        # Add deadline if present
        if grant.deadline:
            data["properties"]["Deadline"] = {
                "date": {"start": grant.deadline}
            }
        
        try:
            response = requests.post(url, headers=NOTION_HEADERS, json=data)
            response.raise_for_status()
            response_data = response.json()
            page_id = response_data.get('id')
            if page_id:
                return page_id  # Return the actual page ID
            else:
                print("Warning: No page ID returned from Notion API")
                return 'error'
        except requests.exceptions.RequestException as e:
            print(f"Error adding grant to Notion: {e}")
            return 'error'
    
    def check_duplicate(self, grant: Grant) -> bool:
        """Check if grant already exists in database"""
        url = f'https://api.notion.com/v1/databases/{self.database_id}/query'
        
        # Query for matching grant name and organization
        filter_data = {
            "and": [
                {
                    "property": "Organization Name",
                    "title": {"equals": grant.organization_name}
                },
                {
                    "property": "Grant Name",
                    "rich_text": {"equals": grant.grant_name}
                }
            ]
        }
        
        try:
            response = requests.post(url, headers=NOTION_HEADERS, json={"filter": filter_data})
            response.raise_for_status()
            results = response.json()
            return len(results.get("results", [])) > 0
        except:
            return False
    
    def generate_report(self, grants: List[Grant]) -> str:
        """Generate a markdown report of found grants"""
        report = f"# Grant Opportunities Report - {datetime.now().strftime('%Y-%m-%d')}\n\n"
        
        # High priority grants
        high_priority = [g for g in grants if g.alignment_score >= 8]
        if high_priority:
            report += "## 🎯 High-Priority Grants (8+ alignment)\n\n"
            for grant in high_priority[:5]:
                report += f"### {grant.grant_name}\n"
                report += f"- **Organization:** {grant.organization_name}\n"
                report += f"- **Alignment:** {grant.alignment_score}/10\n"
                report += f"- **Amount:** {grant.grant_amount}\n"
                report += f"- **Deadline:** {grant.deadline or 'Rolling'}\n"
                report += f"- **Target:** {grant.funding_target.value}\n"
                report += f"- **Link:** {grant.grant_link}\n\n"
        
        # Upcoming deadlines
        upcoming = [g for g in grants if g.deadline]
        upcoming.sort(key=lambda x: x.deadline)
        
        if upcoming:
            report += "## ⏰ Upcoming Deadlines\n\n"
            for grant in upcoming[:5]:
                report += f"- **{grant.deadline}:** {grant.grant_name} ({grant.organization_name})\n"
        
        # Statistics
        report += f"\n## 📊 Statistics\n\n"
        report += f"- Total grants found: {len(grants)}\n"
        report += f"- High alignment (8+): {len(high_priority)}\n"
        report += f"- Average alignment: {sum(g.alignment_score for g in grants) / len(grants):.1f}\n" if grants else ""
        
        return report
    
    def cleanup_expired_grants(self):
        """Remove grants with past deadlines from the database"""
        url = f'https://api.notion.com/v1/databases/{self.database_id}/query'
        today = datetime.now()
        
        # Query all grants
        response = requests.post(url, headers=NOTION_HEADERS, json={})
        if response.status_code != 200:
            return 0
            
        results = response.json().get('results', [])
        deleted_count = 0
        
        for grant in results:
            deadline_prop = grant['properties'].get('Deadline', {})
            deadline_date = deadline_prop.get('date')
            
            if deadline_date and deadline_date.get('start'):
                deadline_str = deadline_date['start']
                try:
                    deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
                    if deadline < today:
                        # Archive (delete) this grant
                        delete_url = f'https://api.notion.com/v1/pages/{grant["id"]}'
                        delete_response = requests.patch(
                            delete_url, 
                            headers=NOTION_HEADERS, 
                            json={'archived': True}
                        )
                        if delete_response.status_code == 200:
                            deleted_count += 1
                except:
                    pass
        
        return deleted_count
    
    def run_daily_search(self):
        """Main execution function for daily grant search"""
        print(f"Starting grant search at {datetime.now()}")
        
        # First, cleanup expired grants
        deleted = self.cleanup_expired_grants()
        if deleted > 0:
            print(f"Cleaned up {deleted} expired grants")
        
        # Search all sources
        grants = self.search_all_sources()
        print(f"Found {len(grants)} potential grants")
        
        # Add new grants to Notion
        added_count = 0
        for grant in grants:
            result = self.add_to_notion_database(grant)
            if result not in ['duplicate', 'expired', 'error']:
                # result is a page_id
                added_count += 1
                print(f"Added: {grant.grant_name} (Alignment: {grant.alignment_score})")
            elif result == 'duplicate':
                print(f"Skipping duplicate: {grant.grant_name}")
            elif result == 'expired':
                print(f"Skipping expired: {grant.grant_name}")
            elif result == 'error':
                print(f"Error adding: {grant.grant_name}")
            time.sleep(0.5)  # Rate limiting
        
        print(f"Added {added_count} new grants to database")
        
        # Generate report
        report = self.generate_report(grants)
        
        # Save report to file
        report_path = f"/Users/home/grant_reports/report_{datetime.now().strftime('%Y%m%d')}.md"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(f"Report saved to {report_path}")
        
        return added_count, report


def main():
    """Main entry point"""
    agent = GrantSearchAgent()
    added_count, report = agent.run_daily_search()
    
    print("\n" + "="*50)
    print(report)
    print("="*50)
    
    return added_count


if __name__ == "__main__":
    main()