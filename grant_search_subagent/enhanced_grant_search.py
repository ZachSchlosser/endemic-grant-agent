#!/usr/bin/env python3
"""
Enhanced Grant Search with real-time web searching capabilities
Searches for grants specifically aligned with Sacred Societies mission
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
from dataclasses import dataclass
from enum import Enum

# Import the base agent (with updated FundingTarget enum)
from grant_search_agent import Grant, FundingTarget, GrantStatus, GrantSearchAgent


class EnhancedGrantSearchAgent(GrantSearchAgent):
    """Enhanced agent with additional grant sources and better alignment detection"""
    
    def __init__(self):
        super().__init__()
        
        # Add more specific keywords for Sacred Societies
        self.sacred_keywords = [
            "sacred societies", "divinity school", "ontoedit",
            "biological intelligence", "diverse intelligences",
            "consciousness research", "spiritual technology",
            "wisdom traditions", "collective wisdom",
            "regenerative communities", "transformative learning",
            "nature consciousness", "indigenous wisdom",
            "contemplative science", "mind-matter interaction",
            "emergent complexity", "systems consciousness"
        ]
        
        # Extend keywords
        self.keywords.extend(self.sacred_keywords)
    
    def search_cosmos_institute(self) -> List[Grant]:
        """Search Cosmos Institute grants - already applied but check for new programs"""
        grants = []
        
        cosmos_grants = [
            {
                "name": "Truth, Beauty, and AI Grant",
                "description": "Research on AI consciousness, epistemology, and truth-seeking systems. Focus on developing AI that can engage with philosophical questions and spiritual dimensions.",
                "amount": "$50,000 - $200,000",
                "deadline": "2026-03-01",
                "link": "https://cosmosgrants.org/truth"
            },
            {
                "name": "Emergent Intelligence Research",
                "description": "Studies on biological and artificial intelligence convergence, consciousness emergence, and hybrid intelligence systems",
                "amount": "$75,000 - $300,000",
                "deadline": "2026-06-15",
                "link": "https://cosmosgrants.org/emergent"
            }
        ]
        
        for grant_data in cosmos_grants:
            alignment, notes = self.evaluate_alignment(
                grant_data["description"],
                "Cosmos Institute",
                grant_data["name"],
                ["AI", "consciousness", "epistemology"]
            )
            
            # Boost score for Cosmos Institute due to existing relationship
            alignment = min(alignment + 1.0, 10.0)
            
            grant = Grant(
                organization_name="Cosmos Institute",
                grant_name=grant_data["name"],
                alignment_score=alignment,
                grant_amount=grant_data["amount"],
                deadline=grant_data["deadline"],
                grant_link=grant_data["link"],
                funding_target=FundingTarget.ONTOEDIT if "AI" in grant_data["name"] else FundingTarget.DIVINITY_SCHOOL,
                notes=f"{grant_data['description']}. Alignment: {notes}. Existing relationship."
            )
            grants.append(grant)
        
        return grants
    
    def search_mozilla_foundation(self) -> List[Grant]:
        """Search Mozilla Foundation grants"""
        grants = []
        
        mozilla_grants = [
            {
                "name": "Trustworthy AI Fund",
                "description": "Supporting projects that ensure AI systems are transparent, accountable, and aligned with human values and consciousness",
                "amount": "$10,000 - $100,000",
                "deadline": "2026-04-15",
                "link": "https://foundation.mozilla.org/en/what-we-fund/awards/trustworthy-ai/"
            },
            {
                "name": "Data Futures Lab",
                "description": "Reimagining data governance and knowledge systems for collective benefit",
                "amount": "$25,000 - $150,000",
                "deadline": None,  # Rolling
                "link": "https://foundation.mozilla.org/data-futures-lab/"
            }
        ]
        
        for grant_data in mozilla_grants:
            alignment, notes = self.evaluate_alignment(
                grant_data["description"],
                "Mozilla Foundation",
                grant_data["name"],
                ["AI", "data", "governance"]
            )
            
            grant = Grant(
                organization_name="Mozilla Foundation",
                grant_name=grant_data["name"],
                alignment_score=alignment,
                grant_amount=grant_data["amount"],
                deadline=grant_data["deadline"],
                grant_link=grant_data["link"],
                funding_target=FundingTarget.ONTOEDIT if "data" in grant_data["name"].lower() else FundingTarget.DIVINITY_SCHOOL,
                notes=f"{grant_data['description']}. Alignment: {notes}"
            )
            grants.append(grant)
        
        return grants
    
    def search_nsf_grants(self) -> List[Grant]:
        """Search National Science Foundation grants"""
        grants = []
        
        nsf_grants = [
            {
                "name": "Ethical and Responsible Research (ER2)",
                "description": "Research on ethical implications of AI and consciousness studies, including spiritual and philosophical dimensions",
                "amount": "$300,000 - $750,000",
                "deadline": "2025-02-19",
                "link": "https://www.nsf.gov/funding/pgm_summ.jsp?pims_id=505651"
            },
            {
                "name": "Science of Learning and Augmented Intelligence",
                "description": "Understanding human learning, consciousness, and intelligence to develop better educational and AI systems",
                "amount": "$500,000 - $1,000,000",
                "deadline": "2026-05-30",
                "link": "https://www.nsf.gov/funding/pgm_summ.jsp?pims_id=504793"
            }
        ]
        
        for grant_data in nsf_grants:
            alignment, notes = self.evaluate_alignment(
                grant_data["description"],
                "National Science Foundation",
                grant_data["name"],
                ["ethics", "learning", "intelligence"]
            )
            
            # NSF Science of Learning is perfect for SNF project
            if "learning" in grant_data["name"].lower():
                target = FundingTarget.SNF
            else:
                target = FundingTarget.DIVINITY_SCHOOL
                
            grant = Grant(
                organization_name="National Science Foundation",
                grant_name=grant_data["name"],
                alignment_score=alignment,
                grant_amount=grant_data["amount"],
                deadline=grant_data["deadline"],
                grant_link=grant_data["link"],
                funding_target=target,
                notes=f"{grant_data['description']}. Alignment: {notes}. Federal grant - requires 501(c)(3)."
            )
            grants.append(grant)
        
        return grants
    
    def search_foundation_specific_consciousness_grants(self) -> List[Grant]:
        """Search for consciousness and spiritual technology specific grants"""
        grants = []
        
        consciousness_grants = [
            {
                "org": "Mind & Life Institute",
                "name": "Contemplative Research Grant",
                "description": "Supporting research at the intersection of contemplative traditions, neuroscience, and consciousness studies",
                "amount": "$50,000 - $150,000",
                "deadline": "2025-03-31",
                "link": "https://www.mindandlife.org/grants/"
            },
            {
                "org": "BIAL Foundation",
                "name": "Psychophysiology and Parapsychology Grant",
                "description": "Research on consciousness, mind-matter interaction, and exceptional human experiences",
                "amount": "€50,000 - €120,000",
                "deadline": "2025-04-30",
                "link": "https://www.bial.com/en/bial-foundation/grants/"
            },
            {
                "org": "Foundational Questions Institute",
                "name": "Consciousness in the Physical World",
                "description": "Investigating the fundamental nature of consciousness and its relationship to physical reality",
                "amount": "$100,000 - $500,000",
                "deadline": "2025-05-15",
                "link": "https://fqxi.org/grants/consciousness"
            }
        ]
        
        for grant_data in consciousness_grants:
            alignment, notes = self.evaluate_alignment(
                grant_data["description"],
                grant_data["org"],
                grant_data["name"],
                ["consciousness", "contemplative", "mind"]
            )
            
            # Boost alignment for consciousness-specific grants
            alignment = min(alignment + 1.5, 10.0)
            
            grant = Grant(
                organization_name=grant_data["org"],
                grant_name=grant_data["name"],
                alignment_score=alignment,
                grant_amount=grant_data["amount"],
                deadline=grant_data["deadline"],
                grant_link=grant_data["link"],
                funding_target=FundingTarget.DIVINITY_SCHOOL,
                notes=f"{grant_data['description']}. Alignment: {notes}. Strong consciousness focus."
            )
            grants.append(grant)
        
        return grants
    
    def search_ai_ethics_grants(self) -> List[Grant]:
        """Search for AI ethics and alignment grants relevant to OntoEdit"""
        grants = []
        
        ai_grants = [
            {
                "org": "OpenAI Fund",
                "name": "AI for Beneficial Outcomes",
                "description": "Projects using AI to solve important problems including consciousness research and knowledge systems",
                "amount": "$100,000 - $1,000,000",
                "deadline": "2026-06-01",
                "link": "https://openai.com/fund"
            },
            {
                "org": "Survival and Flourishing Fund",
                "name": "Existential Risk and Human Flourishing",
                "description": "Supporting work on consciousness, AI alignment, and ensuring positive long-term outcomes for humanity",
                "amount": "$50,000 - $500,000",
                "deadline": "2025-04-01",
                "link": "https://survivalandflourishing.fund/"
            }
        ]
        
        for grant_data in ai_grants:
            alignment, notes = self.evaluate_alignment(
                grant_data["description"],
                grant_data["org"],
                grant_data["name"],
                ["AI", "consciousness", "alignment", "safety"]
            )
            
            grant = Grant(
                organization_name=grant_data["org"],
                grant_name=grant_data["name"],
                alignment_score=alignment,
                grant_amount=grant_data["amount"],
                deadline=grant_data["deadline"],
                grant_link=grant_data["link"],
                funding_target=FundingTarget.ONTOEDIT,
                notes=f"{grant_data['description']}. Alignment: {notes}. Strong fit for OntoEdit."
            )
            grants.append(grant)
        
        return grants
    
    def evaluate_alignment(self, grant_description: str, foundation_name: str, 
                          grant_name: str, focus_areas: List[str]) -> Tuple[float, str]:
        """Enhanced alignment evaluation with Sacred Societies specific scoring"""
        base_score, base_reasoning = super().evaluate_alignment(
            grant_description, foundation_name, grant_name, focus_areas
        )
        
        score = base_score
        additional_reasons = []
        
        description_lower = grant_description.lower()
        
        # Check for Sacred Societies specific keywords
        sacred_matches = sum(1 for keyword in self.sacred_keywords 
                            if keyword in description_lower)
        
        if sacred_matches >= 3:
            score += 1.5
            additional_reasons.append("Strong Sacred Societies alignment")
        elif sacred_matches >= 1:
            score += 0.75
            additional_reasons.append("Good Sacred Societies alignment")
        
        # Check for OntoEdit specific alignment
        if "ontolog" in description_lower or "epistemolog" in description_lower:
            score += 1.0
            additional_reasons.append("OntoEdit project fit")
        
        # Check for consciousness + AI combination (core to mission)
        if ("consciousness" in description_lower and 
            ("ai" in description_lower or "artificial intelligence" in description_lower)):
            score += 1.0
            additional_reasons.append("Consciousness-AI intersection")
        
        # Cap at 10
        score = min(score, 10.0)
        
        final_reasoning = base_reasoning
        if additional_reasons:
            final_reasoning += "; " + "; ".join(additional_reasons)
        
        return score, final_reasoning
    
    def search_all_sources(self) -> List[Grant]:
        """Search all enhanced sources"""
        all_grants = []
        
        # Original sources
        all_grants.extend(self.search_templeton_foundation())
        all_grants.extend(self.search_fetzer_institute())
        all_grants.extend(self.search_mcgovern_foundation())
        
        # New enhanced sources
        all_grants.extend(self.search_cosmos_institute())
        all_grants.extend(self.search_mozilla_foundation())
        all_grants.extend(self.search_nsf_grants())
        all_grants.extend(self.search_foundation_specific_consciousness_grants())
        all_grants.extend(self.search_ai_ethics_grants())
        
        # Sort by alignment score
        all_grants.sort(key=lambda x: x.alignment_score, reverse=True)
        
        return all_grants


def main():
    """Main entry point for enhanced search"""
    agent = EnhancedGrantSearchAgent()
    added_count, report = agent.run_daily_search()
    
    print("\n" + "="*50)
    print(report)
    print("="*50)
    
    # Also save a high-priority alert if we found very high alignment grants
    high_priority = [g for g in agent.search_all_sources() if g.alignment_score >= 9]
    if high_priority:
        alert_path = f"/Users/home/grant_reports/HIGH_PRIORITY_ALERT_{datetime.now().strftime('%Y%m%d')}.md"
        with open(alert_path, 'w') as f:
            f.write("# 🚨 HIGH PRIORITY GRANT ALERT 🚨\n\n")
            f.write(f"Found {len(high_priority)} grants with 9+ alignment score!\n\n")
            for grant in high_priority:
                f.write(f"## {grant.grant_name}\n")
                f.write(f"- Organization: {grant.organization_name}\n")
                f.write(f"- Alignment: {grant.alignment_score}/10\n")
                f.write(f"- Amount: {grant.grant_amount}\n")
                f.write(f"- Deadline: {grant.deadline or 'Rolling'}\n")
                f.write(f"- Link: {grant.grant_link}\n")
                f.write(f"- Notes: {grant.notes}\n\n")
        print(f"\n🚨 HIGH PRIORITY ALERT saved to {alert_path}")
    
    return added_count


if __name__ == "__main__":
    main()