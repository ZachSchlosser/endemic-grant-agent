#!/usr/bin/env python3
"""
Notion Integration Module
Creates and manages Notion pages for grant questions and answers
"""

import os
import requests
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from grant_question_extractor import GrantQuestion
from grant_proposal_generator import ProposalAnswer

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
except ImportError:
    pass  # dotenv not installed, will try environment variables


class NotionIntegration:
    """Manages Notion database and page creation for grants"""
    
    def __init__(self):
        """Initialize Notion API connection"""
        self.api_key = os.getenv('NOTION_API_KEY')
        if not self.api_key:
            raise ValueError("NOTION_API_KEY environment variable not found")
        
        self.database_id = '2557d734-db27-813c-860a-eea78b88020e'
        self.notion_version = '2022-06-28'
        
        # Parent page for all grant questions and answers documents
        self.grant_docs_parent_id = '2567d734-db27-807b-b3be-e6fbad5b72f9'  # Grant Questions and Draft Answers page
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Notion-Version': self.notion_version
        }
        
        self.base_url = 'https://api.notion.com/v1'
    
    def create_grant_questions_page(self, grant_info: Dict, questions: List[GrantQuestion]) -> Optional[str]:
        """Create a Notion page containing grant questions"""
        
        # Format questions for Notion
        question_blocks = self._format_questions_as_blocks(questions)
        
        # Create page title
        page_title = f"Questions: {grant_info['grant_name']}"
        
        # Create the page
        page_data = {
            "parent": {"page_id": self.grant_docs_parent_id},
            "properties": {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": page_title
                            }
                        }
                    ]
                }
            },
            "children": question_blocks
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=page_data
            )
            
            if response.status_code == 200:
                page_id = response.json()['id']
                page_url = response.json()['url']
                print(f"Created questions page: {page_title}")
                return page_url
            else:
                print(f"Error creating questions page: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"Exception creating questions page: {e}")
            return None
    
    def create_grant_answers_page(self, grant_info: Dict, answers: List[ProposalAnswer]) -> Optional[str]:
        """Create a Notion page containing draft answers"""
        
        # Format answers for Notion
        answer_blocks = self._format_answers_as_blocks(answers)
        
        # Create page title
        page_title = f"Draft Answers: {grant_info['grant_name']}"
        
        # Add summary block at the beginning
        summary_block = self._create_summary_block(grant_info, answers)
        all_blocks = [summary_block] + answer_blocks
        
        # Create the page
        page_data = {
            "parent": {"page_id": self.grant_docs_parent_id},
            "properties": {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": page_title
                            }
                        }
                    ]
                }
            },
            "children": all_blocks
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=page_data
            )
            
            if response.status_code == 200:
                page_id = response.json()['id']
                page_url = response.json()['url']
                print(f"Created answers page: {page_title}")
                return page_url
            else:
                print(f"Error creating answers page: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"Exception creating answers page: {e}")
            return None
    
    def update_grant_database_entry(self, grant_id: str, questions_url: str, answers_url: str) -> bool:
        """Update the grant database entry with links to question and answer pages"""
        
        update_data = {
            "properties": {
                "Grant Questions Page": {
                    "url": questions_url
                },
                "Draft Answers Page": {
                    "url": answers_url
                }
            }
        }
        
        try:
            response = requests.patch(
                f"{self.base_url}/pages/{grant_id}",
                headers=self.headers,
                json=update_data
            )
            
            if response.status_code == 200:
                print(f"Updated grant database entry with page links")
                return True
            else:
                print(f"Error updating database entry: {response.status_code}")
                print(f"Response: {response.text}")
                print(f"Grant ID: {grant_id}")
                print(f"Questions URL: {questions_url}")
                print(f"Answers URL: {answers_url}")
                return False
                
        except Exception as e:
            print(f"Exception updating database entry: {e}")
            return False
    
    def _format_questions_as_blocks(self, questions: List[GrantQuestion]) -> List[Dict]:
        """Format questions as Notion blocks"""
        blocks = []
        
        # Add header
        blocks.append({
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": "Grant Application Questions"}
                }]
            }
        })
        
        blocks.append({
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": f"Total Questions: {len(questions)}"}
                }]
            }
        })
        
        blocks.append({"type": "divider", "divider": {}})
        
        # Add each question
        for q in questions:
            # Question header
            header_text = f"Question {q.question_number}"
            if q.word_limit:
                header_text += f" (Max {q.word_limit} words)"
            if not q.required:
                header_text += " [Optional]"
            
            blocks.append({
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": header_text}
                    }]
                }
            })
            
            # Question text
            blocks.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": q.question_text},
                        "annotations": {"bold": True}
                    }]
                }
            })
            
            # Question type
            blocks.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": f"Type: {q.question_type.replace('_', ' ').title()}"},
                        "annotations": {"italic": True}
                    }]
                }
            })
            
            # Add space
            blocks.append({
                "type": "paragraph",
                "paragraph": {"rich_text": []}
            })
        
        return blocks
    
    def _format_answers_as_blocks(self, answers: List[ProposalAnswer]) -> List[Dict]:
        """Format answers as Notion blocks - COMPACT VERSION to stay under 100 block limit"""
        blocks = []
        
        # Single header block
        blocks.append({
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": f"Draft Proposal Answers - Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}"}
                }]
            }
        })
        
        # Calculate metrics for summary
        total_questions = len(answers)
        avg_confidence = sum(a.confidence_score for a in answers) / total_questions if answers else 0
        total_words = sum(a.word_count for a in answers)
        high_confidence = len([a for a in answers if a.confidence_score >= 8])
        
        # Single summary block
        summary_text = f"📋 {total_questions} Questions | 📊 Avg Confidence: {avg_confidence:.1f}/10 | 📝 Total Words: {total_words} | ✅ High Confidence: {high_confidence}"
        blocks.append({
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": summary_text},
                    "annotations": {"color": "gray"}
                }]
            }
        })
        
        blocks.append({"type": "divider", "divider": {}})
        
        # Compact format: Each answer as a single toggle block
        for answer in answers:
            # Create confidence indicator
            confidence_emoji = "🟢" if answer.confidence_score >= 8 else "🟡" if answer.confidence_score >= 6 else "🔴"
            
            # Question as toggle header (limit to 100 chars for readability)
            question_preview = answer.question_text[:97] + "..." if len(answer.question_text) > 100 else answer.question_text
            toggle_title = f"{confidence_emoji} Q{answer.question_number}: {question_preview}"
            
            # Answer content inside toggle (combine everything into rich text)
            toggle_content = []
            
            # Full question text if truncated
            if len(answer.question_text) > 100:
                toggle_content.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": f"Full Question: {answer.question_text}"},
                            "annotations": {"bold": True}
                        }]
                    }
                })
            
            # Answer text - split if too long for Notion's 2000 char limit
            answer_text = answer.answer_text
            if len(answer_text) <= 2000:
                # Single paragraph
                toggle_content.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": answer_text}
                        }]
                    }
                })
            else:
                # Split into multiple paragraphs with enhanced chunking
                chunks = self._split_text_safely(answer_text)
                for chunk in chunks:
                    toggle_content.append({
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{
                                "type": "text",
                                "text": {"content": chunk}
                            }]
                        }
                    })
            
            # Compact metadata as single line
            metadata_text = f"📊 Confidence: {answer.confidence_score}/10 | 📝 Words: {answer.word_count}"
            if answer.notes and not answer.notes.startswith("Generated for"):
                metadata_text += f" | 📎 {answer.notes}"
                
            toggle_content.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": metadata_text},
                        "annotations": {"italic": True, "color": "gray"}
                    }]
                }
            })
            
            # Single toggle block per answer
            blocks.append({
                "type": "toggle",
                "toggle": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": toggle_title}
                    }],
                    "children": toggle_content
                }
            })
        
        print(f"   📦 Created {len(blocks)} blocks (limit: 100)")
        return blocks
    
    def _create_summary_block(self, grant_info: Dict, answers: List[ProposalAnswer]) -> Dict:
        """Create a summary block for the answers page"""
        
        # Calculate statistics
        avg_confidence = sum(a.confidence_score for a in answers) / len(answers) if answers else 0
        total_words = sum(a.word_count for a in answers)
        high_conf = len([a for a in answers if a.confidence_score >= 8])
        needs_review = len([a for a in answers if a.confidence_score < 7])
        
        summary_text = f"""📋 PROPOSAL SUMMARY
        
Grant: {grant_info['grant_name']}
Organization: {grant_info['organization_name']}
Amount: {grant_info['grant_amount']}
Alignment Score: {grant_info['alignment_score']}/10

📊 ANSWER STATISTICS
Total Answers: {len(answers)}
Average Confidence: {avg_confidence:.1f}/10
Total Word Count: {total_words}
High Confidence Answers: {high_conf}
Needs Review: {needs_review}"""
        
        return {
            "type": "callout",
            "callout": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": summary_text}
                }],
                "icon": {"emoji": "📝"},
                "color": "blue_background"
            }
        }
    
    def _split_text_safely(self, text: str, max_length: int = 1900) -> List[str]:
        """Split text into chunks that respect Notion's character limits"""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # First try splitting by sentences
        sentences = text.split('. ')
        
        for sentence in sentences:
            sentence_with_period = sentence + ('. ' if sentence != sentences[-1] else '')
            
            # If this single sentence is too long, split it further
            if len(sentence_with_period) > max_length:
                # Split long sentence by words
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                words = sentence_with_period.split(' ')
                word_chunk = ""
                
                for word in words:
                    test_word_chunk = word_chunk + (' ' if word_chunk else '') + word
                    if len(test_word_chunk) > max_length and word_chunk:
                        chunks.append(word_chunk.strip())
                        word_chunk = word
                    else:
                        word_chunk = test_word_chunk
                
                if word_chunk.strip():
                    current_chunk = word_chunk.strip()
            else:
                # Normal sentence processing
                test_chunk = current_chunk + sentence_with_period
                if len(test_chunk) > max_length and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence_with_period
                else:
                    current_chunk = test_chunk
        
        # Add the final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def get_grant_by_name(self, org_name: str, grant_name: str) -> Optional[Dict]:
        """Find a grant in the database by organization and grant name"""
        
        query_data = {
            "filter": {
                "and": [
                    {
                        "property": "Organization Name",
                        "title": {
                            "contains": org_name
                        }
                    },
                    {
                        "property": "Grant Name",
                        "rich_text": {
                            "contains": grant_name
                        }
                    }
                ]
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/databases/{self.database_id}/query",
                headers=self.headers,
                json=query_data
            )
            
            if response.status_code == 200:
                results = response.json().get('results', [])
                if results:
                    return results[0]
            
            return None
            
        except Exception as e:
            print(f"Error finding grant: {e}")
            return None


def main():
    """Test the Notion integration"""
    from grant_question_extractor import GrantQuestionExtractor
    from grant_proposal_generator import GrantProposalGenerator
    
    # Initialize modules
    notion = NotionIntegration()
    extractor = GrantQuestionExtractor()
    generator = GrantProposalGenerator()
    
    # Test grant
    test_grant = {
        "organization_name": "Test Foundation",
        "grant_name": "Integration Test Grant",
        "grant_amount": "$100,000",
        "alignment_score": 8.5,
        "funding_target": "OntoEdit AI"
    }
    
    # Get test questions
    questions = extractor.generate_generic_questions("Test Foundation")[:3]
    
    # Generate test answers
    print("Generating test answers...")
    answers = generator.generate_proposal_answers(test_grant, questions)
    
    # Create Notion pages
    print("\nCreating Notion pages...")
    questions_url = notion.create_grant_questions_page(test_grant, questions)
    answers_url = notion.create_grant_answers_page(test_grant, answers)
    
    if questions_url and answers_url:
        print(f"\nSuccessfully created pages:")
        print(f"Questions: {questions_url}")
        print(f"Answers: {answers_url}")
    else:
        print("\nFailed to create one or more pages")


if __name__ == "__main__":
    main()