
"""
MITRA AI Email Query Processor
==============================
Advanced query processing engine for email intelligence
Handles complex queries with minimal OpenAI API usage
"""

import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)

class EmailQueryProcessor:
    def __init__(self, workbook_path: str):
        """
        Initialize the Email Query Processor for a specific workbook

        Args:
            workbook_path: Path to transformed workbook data
        """
        self.workbook_path = workbook_path
        self.data_cache = {}
        self.master_index = self._load_master_index()

        # Query complexity patterns for routing decisions
        self.complexity_patterns = {
            'simple': [
                r'(?:name|list|show).*participants',
                r'last.*(?:mail|email)',
                r'first.*(?:mail|email)',
                r'how many.*(?:emails?|participants?)'
            ],
            'computational': [
                r'how many times.*(?:sent|received)',
                r'how many days.*(?:between|from|since)',
                r'count.*(?:files?|submissions?)',
                r'calculate.*(?:time|duration)'
            ],
            'analytical': [
                r'what.*(?:discuss|discussed|about)',
                r'analyze.*',
                r'explain.*',
                r'summarize.*',
                r'overview.*'
            ]
        }

    def _load_master_index(self) -> Dict:
        """Load the master index for the workbook"""
        try:
            index_path = os.path.join(self.workbook_path, 'master_index.json')
            with open(index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading master index: {e}")
            return {}

    def get_query_routing(self, query: str) -> List[str]:
        """Determine which files to load based on query content"""
        query_lower = query.lower()

        # Use master index query routing if available
        query_routing = self.master_index.get('query_routing', {})

        # Determine query type and return appropriate files
        if any(word in query_lower for word in ['participant', 'people', 'who']):
            return query_routing.get('participant_queries', ['participants.json'])

        elif any(word in query_lower for word in ['progress', 'status', 'percent', 'success']):
            return query_routing.get('progress_queries', ['workflow_states.json'])

        elif any(word in query_lower for word in ['issue', 'problem', 'error', 'duplicate']):
            return query_routing.get('issue_queries', ['issues_resolution.json'])

        elif any(word in query_lower for word in ['decision', 'meeting', 'agreed', 'decided']):
            return query_routing.get('decision_queries', ['decisions_actions.json'])

        elif any(word in query_lower for word in ['timeline', 'date', 'when', 'first', 'last']):
            return query_routing.get('timeline_queries', ['timeline.json'])

        elif any(word in query_lower for word in ['business', 'company', 'nikwax', 'paramo', 'percipere']):
            return query_routing.get('business_queries', ['business_context.json'])

        else:
            # Default to semantic clusters for general queries
            return query_routing.get('technical_queries', ['semantic_clusters.json'])

    def analyze_query_complexity(self, query: str) -> str:
        """Analyze query complexity to determine processing approach"""
        query_lower = query.lower()

        for complexity, patterns in self.complexity_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return complexity

        return 'simple'  # Default to simple

    def extract_time_entities(self, query: str) -> Dict:
        """Extract time-related entities from query"""
        time_entities = {
            'months': [],
            'relative_time': [],
            'specific_dates': []
        }

        query_lower = query.lower()

        # Extract months
        months = ['january', 'february', 'march', 'april', 'may', 'june',
                 'july', 'august', 'september', 'october', 'november', 'december']

        for month in months:
            if month in query_lower:
                time_entities['months'].append(month)

        # Extract relative time references
        relative_patterns = [
            r'last \w+',
            r'first \w+',
            r'latest \w+',
            r'recent \w+',
            r'previous \w+'
        ]

        for pattern in relative_patterns:
            matches = re.findall(pattern, query_lower)
            time_entities['relative_time'].extend(matches)

        return time_entities

    def extract_numerical_entities(self, query: str) -> Dict:
        """Extract numerical entities and counting requests"""
        numerical_entities = {
            'counts_requested': [],
            'numbers': [],
            'calculations': []
        }

        query_lower = query.lower()

        # Extract count requests
        count_patterns = [
            r'how many times',
            r'how many \w+',
            r'count \w+',
            r'number of \w+'
        ]

        for pattern in count_patterns:
            matches = re.findall(pattern, query_lower)
            numerical_entities['counts_requested'].extend(matches)

        # Extract explicit numbers
        numbers = re.findall(r'\b\d+\b', query)
        numerical_entities['numbers'] = [int(n) for n in numbers]

        # Extract calculation requests
        if any(word in query_lower for word in ['days', 'between', 'from', 'to', 'duration']):
            numerical_entities['calculations'].append('time_calculation')

        return numerical_entities

    def prepare_minimal_context(self, files_to_load: List[str], entities: Dict) -> Dict:
        """Prepare minimal context data for AI processing"""
        context = {}

        for filename in files_to_load[:3]:  # Limit to 3 files max
            data = self.load_data_file(filename)

            # Filter data based on entities to reduce token usage
            if filename == 'timeline.json' and entities.get('months'):
                # Filter timeline by requested months
                filtered_data = self._filter_timeline_by_months(data, entities['months'])
                context[filename] = filtered_data

            elif filename == 'participants.json' and entities.get('companies'):
                # Filter participants by requested companies
                filtered_data = self._filter_participants_by_companies(data, entities['companies'])
                context[filename] = filtered_data

            elif filename == 'workflow_states.json':
                # Include only essential workflow data
                context[filename] = {
                    'status_summary': data.get('status_summary', {}),
                    'file_versions': data.get('file_versions', [])[-10:],  # Last 10 versions
                    'validation_timeline': data.get('validation_timeline', [])[-10:]  # Last 10 validations
                }

            else:
                # For other files, include limited data
                if isinstance(data, dict):
                    limited_data = {}
                    for key, value in list(data.items())[:5]:  # Max 5 top-level keys
                        if isinstance(value, list):
                            limited_data[key] = value[:10]  # Max 10 items per list
                        else:
                            limited_data[key] = value
                    context[filename] = limited_data
                else:
                    context[filename] = data

        return context

    def _filter_timeline_by_months(self, timeline_data: Dict, months: List[str]) -> Dict:
        """Filter timeline data by specific months"""
        filtered = {'overall': timeline_data.get('overall', {})}

        by_month = timeline_data.get('by_month', {})
        filtered['by_month'] = {}

        for month_name in months:
            try:
                month_num = datetime.strptime(month_name, '%B').month
                for month_key, emails in by_month.items():
                    if f"-{month_num:02d}" in month_key:
                        filtered['by_month'][month_key] = emails
            except ValueError:
                continue

        return filtered

    def _filter_participants_by_companies(self, participants_data: Dict, companies: List[str]) -> Dict:
        """Filter participants by specific companies"""
        filtered = {'senders': {}, 'recipients': {}}

        for participant_type in ['senders', 'recipients']:
            for email, count in participants_data.get(participant_type, {}).items():
                for company in companies:
                    domain_patterns = {
                        'nikwax': 'nikwax.co.uk',
                        'paramo': 'paramo.uk.co',
                        'percipere': 'percipere.co'
                    }

                    if company.lower() in domain_patterns:
                        pattern = domain_patterns[company.lower()]
                        if pattern in email.lower():
                            filtered[participant_type][email] = count
                            break

        return filtered

    def load_data_file(self, filename: str) -> Dict:
        """Load and cache a data file"""
        if filename not in self.data_cache:
            file_path = os.path.join(self.workbook_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.data_cache[filename] = json.load(f)
            except Exception as e:
                logger.error(f"Error loading {filename}: {e}")
                self.data_cache[filename] = {}

        return self.data_cache[filename]

    def compute_file_statistics(self, query: str) -> Dict:
        """Compute file-related statistics without AI"""
        try:
            workflow_states = self.load_data_file('workflow_states.json')

            file_versions = workflow_states.get('file_versions', [])
            validation_timeline = workflow_states.get('validation_timeline', [])

            # Client vs consultant identification
            client_domains = ['nikwax.co.uk', 'paramo.uk.co']
            consultant_domains = ['percipere.co']

            stats = {
                'total_file_versions': len(file_versions),
                'files_to_consultants': 0,
                'validations_back_to_clients': 0,
                'unique_file_versions': len(set(v.get('version', 0) for v in file_versions))
            }

            # Count files sent to consultants
            for version in file_versions:
                sender_email = version.get('sender', '')
                # If sender is from client domain, it's likely sent to consultants
                if any(domain in sender_email.lower() for domain in client_domains):
                    stats['files_to_consultants'] += 1

            # Count validations/reverts back to clients
            for validation in validation_timeline:
                sender_email = validation.get('sender', '')
                # If sender is from consultant domain, it's feedback to clients
                if any(domain in sender_email.lower() for domain in consultant_domains):
                    if 'issues' in validation or 'remaining' in str(validation):
                        stats['validations_back_to_clients'] += 1

            return stats

        except Exception as e:
            logger.error(f"Error computing file statistics: {e}")
            return {}

    def compute_timeline_statistics(self, query: str) -> Dict:
        """Compute timeline-related statistics without AI"""
        try:
            workflow_states = self.load_data_file('workflow_states.json')
            timeline = self.load_data_file('timeline.json')

            validation_timeline = workflow_states.get('validation_timeline', [])
            overall = timeline.get('overall', {})

            stats = {
                'total_emails': 0,
                'first_email_date': overall.get('first_date'),
                'last_email_date': overall.get('last_date'),
                'total_days': 0,
                'first_validation_date': None,
                'last_validation_date': None,
                'validation_period_days': 0
            }

            # Calculate total days
            if stats['first_email_date'] and stats['last_email_date']:
                first_date = datetime.fromisoformat(stats['first_email_date'])
                last_date = datetime.fromisoformat(stats['last_email_date'])
                stats['total_days'] = (last_date - first_date).days

            # Calculate validation period
            if validation_timeline:
                validation_dates = [v.get('date') for v in validation_timeline if v.get('date')]
                if validation_dates:
                    stats['first_validation_date'] = min(validation_dates)
                    stats['last_validation_date'] = max(validation_dates)

                    first_val = datetime.fromisoformat(stats['first_validation_date'])
                    last_val = datetime.fromisoformat(stats['last_validation_date'])
                    stats['validation_period_days'] = (last_val - first_val).days

            return stats

        except Exception as e:
            logger.error(f"Error computing timeline statistics: {e}")
            return {}

    def find_topic_specific_emails(self, topic: str) -> List[Dict]:
        """Find emails related to a specific topic"""
        try:
            semantic_clusters = self.load_data_file('semantic_clusters.json')
            issues_resolution = self.load_data_file('issues_resolution.json')

            topic_lower = topic.lower()
            relevant_emails = []

            # Check semantic clusters
            for cluster_name, email_ids in semantic_clusters.items():
                if topic_lower in cluster_name.lower():
                    relevant_emails.extend(email_ids)

            # Check issues resolution for topic-specific issues
            if 'product code' in topic_lower:
                system_constraints = issues_resolution.get('system_constraints', [])
                for constraint in system_constraints:
                    if 'character length' in constraint.get('description', '').lower():
                        relevant_emails.append(constraint.get('email_id'))

            return list(set(relevant_emails))  # Remove duplicates

        except Exception as e:
            logger.error(f"Error finding topic-specific emails: {e}")
            return []

    def get_workbook_statistics(self) -> Dict:
        """Get overall workbook statistics"""
        master_index = self.master_index

        return {
            'workbook_name': master_index.get('workbook_name', 'Unknown'),
            'total_emails': master_index.get('total_emails', 0),
            'date_range': master_index.get('date_range', {}),
            'statistics': master_index.get('statistics', {}),
            'available_files': master_index.get('transformation_files', [])
        }
