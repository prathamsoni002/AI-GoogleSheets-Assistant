"""
MITRA AI Email Intelligence Handler
===================================
Handles email queries using transformed data with intelligent OpenAI routing
Integrates with the main chatbot.py backend
"""

import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging

# Import OpenAI API handler from existing core module
from core.openai_api import get_ai_response

logger = logging.getLogger(__name__)

class EmailHandler:
    def __init__(self, transform_results_dir="transform/result"):
        """
        Initialize the Email Handler

        Args:
            transform_results_dir: Path to transformed email data
        """
        self.transform_results_dir = transform_results_dir
        self.data_cache = {}
        self.workbooks = self._discover_workbooks()

        # Intent classification patterns - enhanced from your queries
        self.intent_patterns = {
            'participant_query': [
                r'(?:name|list|show).*participants?', 
                r'who.*(?:from|in|at)', 
                r'(?:paramo|nikwax|percipere).*(?:people|members|team)',
                r'participants?.*(?:paramo|nikwax|percipere)',
                r'all.*(?:people|members|participants?)'
            ],
            'timeline_query': [
                r'last.*(?:mail|email)', 
                r'first.*(?:mail|email)',
                r'when.*(?:was|did)',
                r'date.*(?:of|when)',
                r'how many days',
                r'timeline',
                r'chronological'
            ],
            'file_tracking_query': [
                r'how many times.*(?:sent|file)',
                r'file.*(?:sent|received|reverted)',
                r'sent.*(?:to|from).*percipere',
                r'reverted.*back',
                r'submission.*(?:count|times)',
                r'upload.*(?:count|times)',
                r'files?.*received'
            ],
            'content_query': [
                r'what.*(?:discuss|discussed)',
                r'discuss.*(?:about|of)',
                r'about.*product code',
                r'content.*email',
                r'topic.*',
                r'conversation.*about'
            ],
            'summary_query': [
                r'summary.*(?:of|for)',
                r'summarize.*',
                r'overview.*',
                r'(?:month|months?).*(?:summary|emails?)',
                r'(?:may|june|july|august|september|october|november|december).*(?:emails?|summary)'
            ],
            'status_query': [
                r'open.*(?:issues?|queries?|questions?)',
                r'pending.*',
                r'current.*status',
                r'remaining.*issues?',
                r'status.*(?:of|update)',
                r'what.*(?:issues?|problems?).*remain'
            ]
        }

        # Company role classification for client/consultant identification
        self.company_roles = {
            'clients': ['nikwax.co.uk', 'paramo.uk.co'],
            'consultants': ['percipere.co']
        }

        logger.info(f"📧 Email Handler initialized with {len(self.workbooks)} workbooks")

    def _discover_workbooks(self) -> List[Dict]:
        """Discover available transformed workbooks"""
        workbooks = []

        if not os.path.exists(self.transform_results_dir):
            logger.warning(f"Transform results directory not found: {self.transform_results_dir}")
            return workbooks

        try:
            for item in os.listdir(self.transform_results_dir):
                workbook_path = os.path.join(self.transform_results_dir, item)
                if os.path.isdir(workbook_path):
                    master_index_path = os.path.join(workbook_path, 'master_index.json')
                    if os.path.exists(master_index_path):
                        workbooks.append({
                            'name': item,
                            'path': workbook_path,
                            'master_index': master_index_path
                        })
        except Exception as e:
            logger.error(f"Error discovering workbooks: {e}")

        return workbooks

    def is_email_query(self, query: str) -> bool:
        """
        Determine if a query is related to email intelligence
        Enhanced detection beyond just 'email:' prefix
        """
        query_lower = query.lower().strip()

        # Direct email prefix (legacy support)
        if query_lower.startswith('email:'):
            return True

        # Email-specific keywords
        email_keywords = [
            'participants', 'mail', 'email', 'sent', 'received', 'discussion',
            'paramo', 'nikwax', 'percipere', 'product code', 'validation',
            'file', 'upload', 'submission', 'revert', 'days passed'
        ]

        # Intent pattern matching
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return True

        # Company name detection
        companies = ['paramo', 'nikwax', 'percipere']
        if any(company in query_lower for company in companies):
            return True

        # Check for email-specific context
        if any(keyword in query_lower for keyword in email_keywords):
            return True

        return False

    def process_email_query(self, query: str) -> str:
        """
        Main entry point for processing email queries
        Called from chatbot.py
        """
        try:
            # Clean the query
            cleaned_query = query
            if cleaned_query.lower().startswith('email:'):
                cleaned_query = cleaned_query[6:].strip()

            logger.info(f"📧 Processing email query: {cleaned_query[:100]}...")

            # Check if we have any workbooks
            if not self.workbooks:
                return self._no_workbooks_response()

            # For now, use the first available workbook (Product Master)
            # In future versions, this could be made configurable
            current_workbook = self.workbooks[0]

            # Process the query
            result = self._process_single_query(cleaned_query, current_workbook)

            return self._format_response(result)

        except Exception as e:
            logger.error(f"Error processing email query: {e}")
            return f"I'm sorry, I ran into a technical issue while processing your request. Could you try asking again?"

    def _process_single_query(self, query: str, workbook: Dict) -> Dict:
        """Process a single email query against a workbook"""
        # Step 1: Classify intent and extract entities
        intent, confidence = self._classify_intent(query)
        entities = self._extract_entities(query)

        logger.info(f"🎯 Intent: {intent} (confidence: {confidence:.2f})")
        logger.info(f"🏷️  Entities: {entities}")

        # Step 2: Route to appropriate handler
        if intent == 'participant_query':
            return self._handle_participant_query(query, entities, workbook)
        elif intent == 'timeline_query':
            return self._handle_timeline_query(query, entities, workbook)
        elif intent == 'file_tracking_query':
            return self._handle_file_tracking_query(query, entities, workbook)
        elif intent == 'content_query':
            return self._handle_content_query(query, entities, workbook)
        elif intent == 'summary_query':
            return self._handle_summary_query(query, entities, workbook)
        elif intent == 'status_query':
            return self._handle_status_query(query, entities, workbook)
        else:
            return self._handle_general_query(query, entities, workbook)

    def _classify_intent(self, query: str) -> Tuple[str, float]:
        """Classify the intent of the user query"""
        query_lower = query.lower()

        scores = {}
        for intent_type, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1
            scores[intent_type] = score / len(patterns) if patterns else 0

        if not scores or max(scores.values()) == 0:
            return 'general_query', 0.0

        best_intent = max(scores, key=scores.get)
        confidence = scores[best_intent]

        return best_intent, confidence

    def _extract_entities(self, query: str) -> Dict:
        """Extract key entities from the query"""
        entities = {
            'companies': [],
            'time_references': [],
            'topics': [],
            'file_references': []
        }

        query_lower = query.lower()

        # Extract companies
        if 'paramo' in query_lower:
            entities['companies'].append('paramo')
        if 'nikwax' in query_lower:
            entities['companies'].append('nikwax')
        if 'percipere' in query_lower:
            entities['companies'].append('percipere')

        # Extract time references
        months = ['january', 'february', 'march', 'april', 'may', 'june',
                 'july', 'august', 'september', 'october', 'november', 'december']
        for month in months:
            if month in query_lower:
                entities['time_references'].append(month)

        # Extract topics
        if any(term in query_lower for term in ['product code', 'character length']):
            entities['topics'].append('product_code_length')
        if 'validation' in query_lower:
            entities['topics'].append('validation')
        if any(term in query_lower for term in ['file', 'upload', 'submission']):
            entities['topics'].append('file_operations')

        return entities

    def _load_data_file(self, workbook: Dict, filename: str) -> Dict:
        """Load and cache a data file from workbook"""
        cache_key = f"{workbook['name']}:{filename}"

        if cache_key not in self.data_cache:
            file_path = os.path.join(workbook['path'], filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.data_cache[cache_key] = json.load(f)
                logger.debug(f"📄 Loaded {filename} for {workbook['name']}")
            except Exception as e:
                logger.error(f"Error loading {filename}: {e}")
                self.data_cache[cache_key] = {}

        return self.data_cache[cache_key]

    def _handle_participant_query(self, query: str, entities: Dict, workbook: Dict) -> Dict:
        """Handle participant-related queries - Direct lookup, no API cost"""
        try:
            participants = self._load_data_file(workbook, 'participants.json')
            business_context = self._load_data_file(workbook, 'business_context.json')

            if entities['companies']:
                # Filter by specific companies
                result_data = {}

                for company in entities['companies']:
                    company_participants = {'senders': {}, 'recipients': {}}

                    # Determine domain pattern
                    if company == 'percipere':
                        domain_pattern = 'percipere.co'
                    elif company in ['nikwax', 'paramo']:
                        domain_pattern = f"{company}.co.uk" if company == 'nikwax' else f"{company}.uk.co"
                    else:
                        continue

                    # Filter participants by domain
                    for email, count in participants.get('senders', {}).items():
                        if domain_pattern in email.lower():
                            company_participants['senders'][email] = count

                    for email, count in participants.get('recipients', {}).items():
                        if domain_pattern in email.lower():
                            company_participants['recipients'][email] = count

                    result_data[company.title()] = company_participants

                return {
                    'query': query,
                    'answer_type': 'direct_lookup',
                    'result': result_data,
                    'processing_cost': '$0.000',
                    'files_used': ['participants.json', 'business_context.json']
                }
            else:
                # Return all participants organized by company
                organized_data = self._organize_participants_by_company(participants)
                return {
                    'query': query,
                    'answer_type': 'direct_lookup',
                    'result': organized_data,
                    'processing_cost': '$0.000',
                    'files_used': ['participants.json']
                }

        except Exception as e:
            return self._error_response(query, f"Error processing participant query: {e}")

    def _handle_timeline_query(self, query: str, entities: Dict, workbook: Dict) -> Dict:
        """Handle timeline-related queries"""
        try:
            timeline = self._load_data_file(workbook, 'timeline.json')
            conversation_threads = self._load_data_file(workbook, 'conversation_threads.json')

            query_lower = query.lower()

            if 'last mail' in query_lower or 'last email' in query_lower:
                # Direct lookup - no API needed
                overall = timeline.get('overall', {})
                main_thread = conversation_threads.get('main_thread', [])

                last_email_details = main_thread[-1] if main_thread else {}

                return {
                    'query': query,
                    'answer_type': 'direct_lookup',
                    'result': {
                        'last_email_id': overall.get('last'),
                        'last_date': overall.get('last_date'),
                        'subject': last_email_details.get('subject'),
                        'sender': last_email_details.get('sender'),
                        'has_attachments': last_email_details.get('has_attachments')
                    },
                    'processing_cost': '$0.000',
                    'files_used': ['timeline.json', 'conversation_threads.json']
                }

            elif 'first mail' in query_lower or 'first email' in query_lower:
                # Direct lookup for first email
                overall = timeline.get('overall', {})
                main_thread = conversation_threads.get('main_thread', [])

                first_email_details = main_thread[0] if main_thread else {}

                return {
                    'query': query,
                    'answer_type': 'direct_lookup',
                    'result': {
                        'first_email_id': overall.get('first'),
                        'first_date': overall.get('first_date'),
                        'subject': first_email_details.get('subject'),
                        'sender': first_email_details.get('sender')
                    },
                    'processing_cost': '$0.000',
                    'files_used': ['timeline.json', 'conversation_threads.json']
                }

            else:
                # Complex timeline query - use AI
                return self._use_ai_for_query(query, {
                    'timeline': timeline,
                    'conversation_threads': conversation_threads.get('main_thread', [])[:10]
                }, 'timeline_analysis')

        except Exception as e:
            return self._error_response(query, f"Error processing timeline query: {e}")

    def _handle_file_tracking_query(self, query: str, entities: Dict, workbook: Dict) -> Dict:
        """Handle file tracking queries - computational analysis"""
        try:
            workflow_states = self._load_data_file(workbook, 'workflow_states.json')
            semantic_clusters = self._load_data_file(workbook, 'semantic_clusters.json')

            # Prepare context for AI computation
            context_data = {
                'file_versions': workflow_states.get('file_versions', []),
                'validation_timeline': workflow_states.get('validation_timeline', []),
                'upload_emails': semantic_clusters.get('upload_cluster', [])[:10],
                'company_roles': self.company_roles,
                'query_type': 'file_tracking'
            }

            return self._use_ai_for_query(query, context_data, 'computation')

        except Exception as e:
            return self._error_response(query, f"Error processing file tracking query: {e}")

    def _handle_content_query(self, query: str, entities: Dict, workbook: Dict) -> Dict:
        """Handle content analysis queries"""
        try:
            query_lower = query.lower()

            if 'product code' in query_lower:
                # Load product code specific data
                issues_resolution = self._load_data_file(workbook, 'issues_resolution.json')
                decisions_actions = self._load_data_file(workbook, 'decisions_actions.json')

                # Get product code related issues
                system_constraints = issues_resolution.get('system_constraints', [])
                product_code_issues = [
                    issue for issue in system_constraints 
                    if 'character length' in issue.get('description', '').lower() or 
                       'product code' in issue.get('description', '').lower()
                ]

                if not product_code_issues:
                    return {
                        'query': query,
                        'answer_type': 'direct_lookup',
                        'result': 'No product code length discussions found in the email chain.',
                        'processing_cost': '$0.000',
                        'files_used': ['issues_resolution.json']
                    }

                # Use AI for detailed content analysis
                context_data = {
                    'product_code_issues': product_code_issues,
                    'key_decisions': decisions_actions.get('key_decisions', []),
                    'meeting_outcomes': decisions_actions.get('meeting_outcomes', [])
                }

                return self._use_ai_for_query(query, context_data, 'content_analysis')

            else:
                # General content query
                semantic_clusters = self._load_data_file(workbook, 'semantic_clusters.json')
                conversation_threads = self._load_data_file(workbook, 'conversation_threads.json')

                context_data = {
                    'semantic_clusters': semantic_clusters,
                    'recent_emails': conversation_threads.get('main_thread', [])[-5:],  # Last 5 emails
                    'entities': entities
                }

                return self._use_ai_for_query(query, context_data, 'content_analysis')

        except Exception as e:
            return self._error_response(query, f"Error processing content query: {e}")

    def _handle_summary_query(self, query: str, entities: Dict, workbook: Dict) -> Dict:
        """Handle summary queries"""
        try:
            timeline = self._load_data_file(workbook, 'timeline.json')
            conversation_threads = self._load_data_file(workbook, 'conversation_threads.json')
            semantic_clusters = self._load_data_file(workbook, 'semantic_clusters.json')

            # Filter by time period if specified
            if entities['time_references']:
                by_month = timeline.get('by_month', {})
                relevant_months = {}

                for month_name in entities['time_references']:
                    try:
                        month_num = datetime.strptime(month_name, '%B').month
                        for month_key, email_ids in by_month.items():
                            if f"-{month_num:02d}" in month_key:
                                relevant_months[month_key] = email_ids
                    except ValueError:
                        continue

                if not relevant_months:
                    return {
                        'query': query,
                        'answer_type': 'direct_lookup',
                        'result': f'No emails found for the specified months: {entities["time_references"]}',
                        'processing_cost': '$0.000',
                        'files_used': ['timeline.json']
                    }

                context_data = {
                    'time_period': entities['time_references'],
                    'relevant_emails': relevant_months,
                    'email_clusters': semantic_clusters
                }

                return self._use_ai_for_query(query, context_data, 'summarization')

            else:
                # General summary
                context_data = {
                    'timeline': timeline,
                    'main_thread': conversation_threads.get('main_thread', []),
                    'clusters': semantic_clusters
                }

                return self._use_ai_for_query(query, context_data, 'summarization')

        except Exception as e:
            return self._error_response(query, f"Error processing summary query: {e}")

    def _handle_status_query(self, query: str, entities: Dict, workbook: Dict) -> Dict:
        """Handle status-related queries - mostly direct lookup"""
        try:
            issues_resolution = self._load_data_file(workbook, 'issues_resolution.json')
            workflow_states = self._load_data_file(workbook, 'workflow_states.json')

            # Get current status information
            status_summary = workflow_states.get('status_summary', {})
            active_issues = issues_resolution.get('data_quality_issues', [])
            critical_issues = issues_resolution.get('critical_issues', [])
            system_constraints = issues_resolution.get('system_constraints', [])

            return {
                'query': query,
                'answer_type': 'computed_summary',
                'result': {
                    'current_status': status_summary.get('current_status', 'Unknown'),
                    'latest_progress': status_summary.get('latest_progress'),
                    'remaining_issues': status_summary.get('remaining_issues'),
                    'active_issues_count': len(active_issues),
                    'critical_issues_count': len(critical_issues),
                    'system_constraints_count': len(system_constraints),
                    'recent_issues': active_issues[-3:] if active_issues else [],
                    'critical_issues': critical_issues
                },
                'processing_cost': '$0.000',
                'files_used': ['issues_resolution.json', 'workflow_states.json']
            }

        except Exception as e:
            return self._error_response(query, f"Error processing status query: {e}")

    def _handle_general_query(self, query: str, entities: Dict, workbook: Dict) -> Dict:
        """Handle general queries that don't fit specific patterns"""
        try:
            semantic_clusters = self._load_data_file(workbook, 'semantic_clusters.json')
            conversation_threads = self._load_data_file(workbook, 'conversation_threads.json')

            context_data = {
                'query_entities': entities,
                'semantic_clusters': semantic_clusters,
                'recent_conversations': conversation_threads.get('main_thread', [])[-10:]
            }

            return self._use_ai_for_query(query, context_data, 'general_analysis')

        except Exception as e:
            return self._error_response(query, f"Error processing general query: {e}")

    def _use_ai_for_query(self, query: str, context_data: Dict, analysis_type: str) -> Dict:
        """Use AI for complex queries requiring analysis"""
        try:
            # Create specialized prompts based on analysis type
            prompt = self._create_ai_prompt(query, context_data, analysis_type)

            # Get AI response using existing core function
            ai_response = get_ai_response(prompt)

            # Estimate token usage and cost
            estimated_tokens = len(prompt.split()) * 1.3  # Rough estimation
            estimated_cost = self._estimate_cost(estimated_tokens, analysis_type)

            return {
                'query': query,
                'answer_type': f'ai_{analysis_type}',
                'result': ai_response,
                'processing_cost': estimated_cost,
                'estimated_tokens': int(estimated_tokens),
                'files_used': list(context_data.keys())[:3]
            }

        except Exception as e:
            return self._error_response(query, f"AI processing error: {e}")

    def _create_ai_prompt(self, query: str, context_data: Dict, analysis_type: str) -> str:
        """Create specialized AI prompts based on analysis type"""

        base_context = f"""You are MITRA AI, an intelligent email analysis assistant for the Product Master migration project.

QUERY: {query}

CONTEXT DATA:
{json.dumps(context_data, indent=2)[:4000]}...

"""

        if analysis_type == 'computation':
            return base_context + """
INSTRUCTIONS FOR COMPUTATION:
- Count occurrences accurately based on the provided data
- Identify client vs consultant roles:
  * Clients: nikwax.co.uk, paramo.uk.co domains
  * Consultants: percipere.co domain
- Provide specific numbers, dates, and email references
- Calculate time differences in days when requested
- Be precise and show your calculations
"""

        elif analysis_type == 'content_analysis':
            return base_context + """
INSTRUCTIONS FOR CONTENT ANALYSIS:
- Focus on the specific topic mentioned in the query
- Extract key discussion points, decisions, and outcomes
- Identify who raised issues vs who provided solutions
- Include relevant dates, email subjects, and participant names
- Explain the discussion flow chronologically
- Highlight any resolutions or decisions made
"""

        elif analysis_type == 'timeline_analysis':
            return base_context + """
INSTRUCTIONS FOR TIMELINE ANALYSIS:
- Analyze the chronological flow of events
- Calculate time periods and durations accurately
- Identify key milestones and turning points
- Show relationships between events
- Include specific dates and time references
"""

        elif analysis_type == 'summarization':
            return base_context + """
INSTRUCTIONS FOR SUMMARIZATION:
- Organize summary by key themes and timeline
- Highlight important decisions, milestones, and outcomes
- Include participant names and their key contributions
- Group related activities and discussions
- Keep summary comprehensive but well-structured
- Focus on business impact and progress
"""

        else:  # general_analysis
            return base_context + """
INSTRUCTIONS FOR GENERAL ANALYSIS:
- Analyze the query in context of the email data provided
- Provide relevant information based on available data
- If specific data isn't available, clearly state this
- Focus on factual information from the emails
- Structure your response clearly and logically
"""

    def _estimate_cost(self, tokens: float, analysis_type: str) -> str:
        """Estimate API cost based on tokens and analysis type"""
        if analysis_type in ['computation', 'timeline_analysis']:
            # GPT-4o-mini pricing: ~$0.0005/1K tokens
            cost = (tokens / 1000) * 0.0005
        else:
            # GPT-4 pricing: ~$0.03/1K tokens for complex analysis
            cost = (tokens / 1000) * 0.03

        if cost < 0.001:
            return '$0.000'
        else:
            return f'${cost:.3f}'

    def _organize_participants_by_company(self, participants: Dict) -> Dict:
        """Organize participants by company domains"""
        organized = {
            'Nikwax': {'senders': {}, 'recipients': {}},
            'Paramo': {'senders': {}, 'recipients': {}},
            'Percipere': {'senders': {}, 'recipients': {}}
        }

        domain_mapping = {
            'nikwax.co.uk': 'Nikwax',
            'paramo.uk.co': 'Paramo',
            'percipere.co': 'Percipere'
        }

        for participant_type in ['senders', 'recipients']:
            for email, count in participants.get(participant_type, {}).items():
                for domain, company in domain_mapping.items():
                    if domain in email.lower():
                        organized[company][participant_type][email] = count
                        break

        return organized

    def _error_response(self, query: str, error_msg: str) -> Dict:
        """Create standardized error response"""
        return {
            'query': query,
            'answer_type': 'error',
            'result': error_msg,
            'processing_cost': '$0.000'
        }

    def _no_workbooks_response(self) -> str:
        """Response when no transformed workbooks are available"""
        return """Sorry, I don't have any email data to analyze right now. To get started, you'll need to:
        1. Run the email transformation:
        
        2. Make sure the transformed data is in the `transform/result/` folder

        Once that's done, you can ask me things like:
        - "Who are all the participants from Nikwax?"
        - "What was the last email about?"
        - "How many files were sent to Percipere?"
        - "What discussions happened about product codes?"

        Let me know when the transformation is complete and I'll be happy to help analyze your emails!"""

    def _format_response(self, result: Dict) -> str:
        """Format the query result into a natural, conversational response"""
        try:
            answer_type = result.get('answer_type', 'unknown')
            main_result = result.get('result')
            
            # Handle errors naturally
            if answer_type == 'error':
                return f"I'm sorry, I ran into an issue: {main_result}. Could you try rephrasing your question?"
            
            # Handle different types of responses conversationally
            if answer_type == 'direct_lookup':
                return self._format_direct_response(main_result, result.get('query', ''))
            
            elif answer_type.startswith('ai_'):
                return self._format_ai_response(main_result)
            
            elif answer_type == 'computed_summary':
                return self._format_status_response(main_result)
            
            else:
                return str(main_result)
        
        except Exception as e:
            return f"I apologize, but I'm having trouble processing that information right now. Could you try asking again?"

    def _format_direct_response(self, data, query: str) -> str:
        """Format direct lookup responses conversationally"""
        query_lower = query.lower()
        
        # Handle participant queries
        if 'participant' in query_lower or 'who' in query_lower:
            if isinstance(data, dict):
                response = "Here are the people involved:\n\n"
                
                for company, details in data.items():
                    if isinstance(details, dict) and 'senders' in details:
                        total_people = len(details.get('senders', {})) + len(details.get('recipients', {}))
                        if total_people > 0:
                            response += f"**{company}:** {total_people} people\n"
                            
                            # Show key participants
                            senders = details.get('senders', {})
                            if senders:
                                top_sender = max(senders.items(), key=lambda x: x[1])
                                response += f"• Most active: {top_sender[0]} ({top_sender[1]} emails sent)\n"
                            
                            response += "\n"
                
                return response.strip()
        
        # Handle timeline queries
        elif 'last' in query_lower or 'first' in query_lower or 'when' in query_lower:
            if isinstance(data, dict):
                if 'last_email_id' in data:
                    response = f"The last email was {data.get('last_email_id', 'unknown')} "
                    if data.get('last_date'):
                        date_str = data['last_date'].split('T')[0] if 'T' in data['last_date'] else data['last_date']
                        response += f"on {date_str}"
                    
                    if data.get('sender'):
                        response += f" from {data['sender']}"
                    
                    if data.get('subject'):
                        response += f" with subject: \"{data['subject']}\""
                    
                    return response + "."
                
                elif 'first_email_id' in data:
                    response = f"The first email was {data.get('first_email_id', 'unknown')} "
                    if data.get('first_date'):
                        date_str = data['first_date'].split('T')[0] if 'T' in data['first_date'] else data['first_date']
                        response += f"on {date_str}"
                    
                    if data.get('sender'):
                        response += f" from {data['sender']}"
                    
                    if data.get('subject'):
                        response += f" with subject: \"{data['subject']}\""
                    
                    return response + "."
        
        # Default formatting for other direct responses
        if isinstance(data, str):
            return data
        else:
            return "I found the information, but let me know if you need more specific details."

    def _format_ai_response(self, ai_result: str) -> str:
        """Format AI responses to be more conversational"""
        # Clean up any technical formatting from AI response
        cleaned_response = ai_result.strip()
        
        # Remove any system-like formatting
        if cleaned_response.startswith("Based on"):
            cleaned_response = cleaned_response.replace("Based on the provided data, ", "")
            cleaned_response = cleaned_response.replace("Based on the email data, ", "")
        
        # Add conversational touches if the response is very formal
        if len(cleaned_response.split('.')) == 1:  # Single sentence
            return cleaned_response
        
        # For longer responses, ensure they flow naturally
        return cleaned_response

    def _format_status_response(self, data: Dict) -> str:
        """Format status responses conversationally"""
        response = ""
        
        current_status = data.get('current_status', 'Unknown')
        if current_status != 'Unknown':
            response += f"The current status is: {current_status}\n\n"
        
        # Progress information
        if data.get('latest_progress'):
            progress = data['latest_progress']
            percent = progress.get('progress_percent', 'N/A')
            if percent != 'N/A':
                response += f"We're {percent}% complete"
                if progress.get('date'):
                    date_str = progress['date'].split('T')[0]
                    response += f" as of {date_str}"
                response += ".\n\n"
        
        # Issues summary
        active_count = data.get('active_issues_count', 0)
        critical_count = data.get('critical_issues_count', 0)
        
        if critical_count > 0:
            response += f"There are {critical_count} critical issues that need attention"
            if active_count > critical_count:
                response += f" and {active_count - critical_count} other active issues"
            response += ".\n\n"
        elif active_count > 0:
            response += f"There are {active_count} active issues being worked on.\n\n"
        else:
            response += "No major issues reported.\n\n"
        
        # Show critical issues if any
        if data.get('critical_issues'):
            response += "The critical issues are:\n"
            for i, issue in enumerate(data['critical_issues'][:3], 1):
                description = issue.get('description', 'Unknown issue')
                response += f"{i}. {description}\n"
        
        return response.strip()

