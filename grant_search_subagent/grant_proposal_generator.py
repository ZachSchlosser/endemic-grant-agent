#!/usr/bin/env python3
"""
Grant Proposal Generator - Integration Module
Connects grant search with Endemic Grant Agent's proposal generation capabilities
"""

import sys
import os
import json
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Add parent directory to access Endemic Grant Agent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
except ImportError:
    pass  # dotenv not installed, will try environment variables

# Import Endemic Grant Agent modules
from auth import GoogleAuth
from ai_jargon_replacer import AIJargonReplacer
import proposal_validator
from grant_question_extractor import GrantQuestion

# Import Anthropic for proposal generation
import anthropic


@dataclass
class ProposalAnswer:
    """Represents an answer to a grant question"""
    question_number: int
    question_text: str
    answer_text: str
    confidence_score: float  # 0-10 scale
    notes: str
    word_count: int


class GrantProposalGenerator:
    """Generates grant proposal answers using Endemic Grant Agent capabilities"""
    
    def __init__(self):
        """Initialize the proposal generator"""
        # Set up Anthropic API client
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            # For development - you can set this directly or use environment variable
            print("Warning: ANTHROPIC_API_KEY not found in environment. Using default.")
            api_key = "your_anthropic_api_key_here"  # Replace with actual key for testing
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.google_auth = GoogleAuth()
        self.jargon_replacer = AIJargonReplacer()
        
        # Load complete Endemic Grant Agent context
        self.endemic_context = self.load_full_context()
        
        # Funder-specific templates
        self.funder_templates = {
            "Cosmos Institute": "visionary",
            "Templeton Foundation": "philosophical",
            "Mozilla Foundation": "technical",
            "NSF": "academic",
            "Mind & Life Institute": "contemplative",
            "BIAL Foundation": "consciousness",
            "Future of Humanity Institute": "existential",
            "OpenAI Fund": "ai_innovation"
        }
    
    def load_full_context(self) -> Dict:
        """Load complete Endemic Grant Agent context from CLAUDE.md and project files"""
        
        # Load CLAUDE.md content
        claude_md_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'CLAUDE.md')
        claude_md_content = ""
        if os.path.exists(claude_md_path):
            with open(claude_md_path, 'r', encoding='utf-8') as f:
                claude_md_content = f.read()
        
        context = {
            "claude_md_full": claude_md_content,
            
            "mission": """The Divinity School is an innovative one-year Certificate in Leadership program designed to develop transformative leaders who can:
            - 'See deeper into reality'
            - 'Make decisions that benefit the whole'
            - 'Align humanity with the natural intelligence of the universe'""",
            
            "core_framework": {
                "developing_novel_futures": {
                    "horizons_biological_intelligence": "Exploring natural intelligence systems",
                    "naturalizing_machine_agency": "Understanding AI as part of natural evolution"
                },
                "four_powers": {
                    "visionary_scholarship": "Deep intellectual exploration beyond conventional boundaries",
                    "awakened_perception": "Enhanced awareness and consciousness", 
                    "crazy_wisdom": "Unconventional insights that challenge established paradigms",
                    "passionate_action": "Transforming vision into real-world impact"
                },
                "moving_institutions": "Creating systemic change through institutional transformation and new organizational models"
            },
            
            "key_projects": {
                "SNF": {
                    "name": "Securing the Nation's Future with Advanced Intelligences",
                    "focus": "Educational transformation for the AI era",
                    "goals": [
                        "Developing metacognitive skills for human-AI collaboration",
                        "National curriculum development for AI literacy",
                        "Preserving human agency and creativity"
                    ],
                    "url": "https://www.endemic.org/divinity-school-snf"
                },
                "futures_we_shape": {
                    "name": "The Futures We Must Shape",
                    "focus": "Bi-annual alignment briefing for executives",
                    "goals": [
                        "Research-driven narrative insights",
                        "Strategic guidance for investment and policy",
                        "Members-only strategy calls"
                    ],
                    "url": "https://www.endemic.org/the-divinity-school-futures-we-shape"
                },
                "ontoedit_ai": {
                    "name": "OntoEdit AI",
                    "focus": "Cognitive widget identification system",
                    "goals": [
                        "Reveals hidden mental frameworks in scientific research",
                        "Promotes metaphysical flexibility",
                        "Transforms conceptual boundaries of scientific thinking"
                    ],
                    "url": "https://www.endemic.org/divinity-school-ontoedit-ai"
                }
            },
            
            "program_details": {
                "duration": "One-year intensive certificate program",
                "format": "150 hours live calls + 200 hours async/self-study",
                "retreat": "Four-day in-person experience in France",
                "cohort_size": "48 students maximum",
                "tuition": "$12,000",
                "future_path": "Working toward MA in Leadership accreditation"
            },
            
            "leadership": {
                "academic_director": "Bonnitta Roy - Process philosopher and futurist",
                "focus_areas": "4E cognitive science, phenomenology, metaphysics",
                "approach": "Integration of technology, spirituality, and ecological intelligence"
            },
            
            "key_messaging_themes": {
                "educational_innovation": [
                    "AI-era leadership preparation",
                    "Metacognitive skill development", 
                    "Human agency preservation",
                    "Institutional transformation"
                ],
                "consciousness_research": [
                    "Diverse intelligences exploration",
                    "Process philosophy applications",
                    "Phenomenological investigations",
                    "Human-AI collaboration models"
                ],
                "leadership_development": [
                    "Four Powers methodology",
                    "Transformative vs. transactional leadership",
                    "Visionary capacity building",
                    "Systems-level impact"
                ],
                "societal_transformation": [
                    "Civilizational challenges",
                    "Future-shaping capabilities",
                    "Cross-sector coordination",
                    "Long-term vision"
                ]
            },
            
            "funder_guidance": {
                "innovation_focused": {
                    "principles": [
                        "Frame as civilizational progress, not incremental improvement",
                        "Emphasize entrepreneurial experimentation",
                        "Show potential for massive social/economic returns",
                        "Acknowledge failure possibility while emphasizing breakthrough potential"
                    ]
                },
                "institutional_foundations": {
                    "principles": [
                        "Focus on systemic change, not incremental improvements",
                        "Strong methodology and prior research",
                        "Write for academic-level scrutiny",
                        "Show how project fits larger ecosystem"
                    ]
                }
            }
        }
        return context
    
    def generate_proposal_answers(self, grant_info: Dict, questions: List[GrantQuestion]) -> List[ProposalAnswer]:
        """Generate answers for all grant questions"""
        answers = []
        
        for question in questions:
            answer = self.generate_single_answer(
                grant_info=grant_info,
                question=question
            )
            answers.append(answer)
            
            # Small delay to avoid rate limiting
            time.sleep(1)
        
        return answers
    
    def generate_single_answer(self, grant_info: Dict, question: GrantQuestion) -> ProposalAnswer:
        """Generate answer for a single question using Claude"""
        
        # Determine writing style based on funder
        funder = grant_info.get("organization_name", "")
        style = self.funder_templates.get(funder, "professional")
        
        # Build the prompt
        prompt = self.build_answer_prompt(grant_info, question, style)
        
        try:
            # Call Claude for answer generation
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            answer_text = response.content[0].text
            
            # Apply jargon replacement
            answer_text, _ = self.jargon_replacer.analyze_text(answer_text)
            
            # Validate word count if limit exists
            if question.word_limit:
                answer_text = self.trim_to_word_limit(answer_text, question.word_limit)
            
            # Calculate confidence score
            confidence = self.calculate_confidence(grant_info, question, answer_text)
            
            return ProposalAnswer(
                question_number=question.question_number,
                question_text=question.question_text,
                answer_text=answer_text,
                confidence_score=confidence,
                notes=f"Generated for {funder} using {style} style",
                word_count=len(answer_text.split())
            )
            
        except Exception as e:
            print(f"Error generating answer: {e}")
            return ProposalAnswer(
                question_number=question.question_number,
                question_text=question.question_text,
                answer_text="[Error generating answer - please write manually]",
                confidence_score=0.0,
                notes=f"Error: {str(e)}",
                word_count=0
            )
    
    def build_answer_prompt(self, grant_info: Dict, question: GrantQuestion, style: str) -> str:
        """Build the prompt for answer generation"""
        
        # Get relevant project based on funding target
        funding_target = grant_info.get("funding_target", "Divinity School Overall")
        
        # Map funding target to project context
        project_mapping = {
            "OntoEdit AI": "ontoedit_ai",
            "SNF": "SNF", 
            "Futures We Must Shape": "futures_we_shape"
        }
        
        project_key = project_mapping.get(funding_target, "SNF")  # Default to SNF
        project_context = self.endemic_context["key_projects"].get(project_key, {})
        
        # Get funder-specific guidance
        funder = grant_info.get('organization_name', '')
        funder_type = "innovation_focused"  # Default
        if any(word in funder.lower() for word in ["foundation", "institute", "trust"]):
            funder_type = "institutional_foundations"
        
        funder_guidance = self.endemic_context["funder_guidance"].get(funder_type, {})
        
        prompt = f"""You are a grant proposal writer for Sacred Societies' Divinity School, an innovative leadership program that develops transformative leaders who can "see deeper into reality," "make decisions that benefit the whole," and "align humanity with the natural intelligence of the universe."

=== COMPLETE ENDEMIC GRANT AGENT CONTEXT ===

{self.endemic_context.get('claude_md_full', '')}

=== CURRENT GRANT CONTEXT ===
- Funder: {grant_info.get('organization_name')}
- Grant Name: {grant_info.get('grant_name')}
- Grant Amount: {grant_info.get('grant_amount')}
- Funding Target Project: {funding_target}
- Grant Link: {grant_info.get('grant_link', 'Not provided')}
- Alignment Score: {grant_info.get('alignment_score')}/10
- Deadline: {grant_info.get('deadline', 'Not specified')}

=== SPECIFIC QUESTION TO ANSWER ===
Question: {question.question_text}
Question Type: {question.question_type}
Word Limit: {question.word_limit if question.word_limit else 'No specific limit'}
Required: {'Yes' if question.required else 'Optional'}

=== PROJECT DETAILS FOR THIS GRANT ===
Project Name: {project_context.get('name', funding_target)}
Project Focus: {project_context.get('focus', '')}
Project Goals: {project_context.get('goals', [])}
Project URL: {project_context.get('url', '')}

=== DIVINITY SCHOOL CORE CONTEXT ===
Mission: {self.endemic_context['mission']}

Four Powers Framework:
1. Visionary Scholarship: {self.endemic_context['core_framework']['four_powers']['visionary_scholarship']}
2. Awakened Perception: {self.endemic_context['core_framework']['four_powers']['awakened_perception']}
3. Crazy Wisdom: {self.endemic_context['core_framework']['four_powers']['crazy_wisdom']}
4. Passionate Action: {self.endemic_context['core_framework']['four_powers']['passionate_action']}

Program Details:
- Duration: {self.endemic_context['program_details']['duration']}
- Format: {self.endemic_context['program_details']['format']}
- Cohort Size: {self.endemic_context['program_details']['cohort_size']}
- Leadership: {self.endemic_context['leadership']['academic_director']}

=== FUNDER-SPECIFIC GUIDANCE ===
Funder Type: {funder_type}
Key Principles for this funder type:
{chr(10).join('- ' + principle for principle in funder_guidance.get('principles', []))}

=== MESSAGING THEMES TO EMPHASIZE ===
Educational Innovation: {', '.join(self.endemic_context['key_messaging_themes']['educational_innovation'])}
Consciousness Research: {', '.join(self.endemic_context['key_messaging_themes']['consciousness_research'])}
Leadership Development: {', '.join(self.endemic_context['key_messaging_themes']['leadership_development'])}
Societal Transformation: {', '.join(self.endemic_context['key_messaging_themes']['societal_transformation'])}

=== WRITING INSTRUCTIONS ===
Style: {style} 
1. Answer the question directly and compellingly
2. Draw specifically from the Sacred Societies mission, Four Powers framework, and project details above
3. Use the funder-specific guidance to tailor your language and approach
4. Include concrete examples from the Divinity School program and projects
5. Frame as transformative, systemic change rather than incremental improvement
6. Include specific metrics, timelines, and outcomes where appropriate
7. Match the funder's communication style and expectations
8. Avoid generic AI language - write with the unique voice and vision of Sacred Societies
9. Stay within word limit: {question.word_limit if question.word_limit else 'No limit specified'}
10. Reference the specific project this grant would fund: {funding_target}

Now write a compelling, tailored grant proposal answer:"""
        
        return prompt
    
    def calculate_confidence(self, grant_info: Dict, question: GrantQuestion, answer: str) -> float:
        """Calculate confidence score for the generated answer"""
        confidence = 5.0  # Base score
        
        # Boost for high alignment grants
        alignment = grant_info.get("alignment_score", 5.0)
        if alignment >= 9.0:
            confidence += 2.0
        elif alignment >= 7.0:
            confidence += 1.0
        
        # Boost for questions matching our strengths
        question_lower = question.question_text.lower()
        if any(word in question_lower for word in ["consciousness", "intelligence", "leadership", "transformation"]):
            confidence += 1.0
        
        # Boost for appropriate length
        word_count = len(answer.split())
        if question.word_limit and word_count <= question.word_limit:
            confidence += 0.5
        
        # Penalty for very short answers
        if word_count < 50 and question.question_type == "essay":
            confidence -= 1.0
        
        # Cap at 10
        return min(confidence, 10.0)
    
    def trim_to_word_limit(self, text: str, word_limit: int) -> str:
        """Trim text to word limit while maintaining coherence"""
        words = text.split()
        if len(words) <= word_limit:
            return text
        
        # Trim to limit and try to end at sentence
        trimmed_words = words[:word_limit]
        trimmed_text = ' '.join(trimmed_words)
        
        # Find last complete sentence
        last_period = trimmed_text.rfind('.')
        if last_period > word_limit * 0.8:  # Keep if we retain 80% of allowed words
            return trimmed_text[:last_period + 1]
        
        return trimmed_text
    
    def create_proposal_document(self, grant_info: Dict, questions: List[GrantQuestion], 
                                answers: List[ProposalAnswer]) -> str:
        """Create a complete proposal document"""
        
        document = f"""# Grant Proposal Draft
## {grant_info['organization_name']} - {grant_info['grant_name']}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Alignment Score:** {grant_info['alignment_score']}/10
**Amount:** {grant_info['grant_amount']}
**Deadline:** {grant_info.get('deadline', 'Rolling')}

---

## Proposal Answers

"""
        
        for answer in answers:
            document += f"""### Question {answer.question_number}
**{answer.question_text}**

{answer.answer_text}

*[Confidence: {answer.confidence_score}/10 | Words: {answer.word_count}]*

---

"""
        
        # Add review notes
        document += """## Review Notes

### High Confidence Answers
"""
        high_conf = [a for a in answers if a.confidence_score >= 8.0]
        for answer in high_conf:
            document += f"- Question {answer.question_number} ({answer.confidence_score}/10)\n"
        
        document += """
### Needs Review
"""
        low_conf = [a for a in answers if a.confidence_score < 7.0]
        for answer in low_conf:
            document += f"- Question {answer.question_number}: {answer.notes}\n"
        
        return document
    
    # Google Docs integration removed - system is now fully automated via Notion
    # All proposals are created directly in Notion for streamlined workflow


def main():
    """Test the proposal generator"""
    generator = GrantProposalGenerator()
    
    # Test grant info
    test_grant = {
        "organization_name": "Cosmos Institute",
        "grant_name": "Truth, Beauty, and AI Grant",
        "grant_amount": "$50,000 - $200,000",
        "alignment_score": 10.0,
        "funding_target": "OntoEdit AI",
        "deadline": "2025-03-01"
    }
    
    # Test questions
    from grant_question_extractor import GrantQuestion
    test_questions = [
        GrantQuestion(1, "Pitch yourself in 1-2 sentences.", "short_answer", word_limit=50),
        GrantQuestion(2, "What is your innovative approach to AI consciousness?", "essay", word_limit=500)
    ]
    
    print("Generating proposal answers...")
    answers = generator.generate_proposal_answers(test_grant, test_questions)
    
    print("\nGenerated Answers:")
    for answer in answers:
        print(f"\nQ{answer.question_number}: {answer.question_text}")
        print(f"Answer: {answer.answer_text}")
        print(f"Confidence: {answer.confidence_score}/10")
        print(f"Word Count: {answer.word_count}")


if __name__ == "__main__":
    main()