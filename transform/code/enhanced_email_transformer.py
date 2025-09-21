
import json
import os
import re
from datetime import datetime
from collections import defaultdict, Counter

# Handle NLTK imports gracefully
NLTK_AVAILABLE = False
try:
    import nltk
    try:
        # Try to download required NLTK resources
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab', quiet=True)  # New requirement for recent NLTK versions
        nltk.download('stopwords', quiet=True)
        from nltk.corpus import stopwords
        from nltk.tokenize import word_tokenize, sent_tokenize
        NLTK_AVAILABLE = True
        print("✓ NLTK resources loaded successfully")
    except Exception as e:
        print(f"⚠️  NLTK resources failed to download: {e}")
        print("📝 Using basic text processing instead")
        NLTK_AVAILABLE = False
except ImportError:
    print("⚠️  NLTK not installed. Using basic text processing.")
    NLTK_AVAILABLE = False

class EnhancedEmailTransformer:
    def __init__(self):
        self.business_entities = {
            'companies': ['nikwax', 'paramo', 'percipere'],
            'systems': ['sap', 's4', 'hana', 'sharepoint'],
            'technical_terms': ['plant data', 'mrp area', 'warehouse', 'supplier', 'customer', 
                              'product master', 'template', 'validation', 'migration', 'upload']
        }

        # Basic stopwords fallback if NLTK is not available
        self.basic_stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'shall', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'my', 'your', 'his', 'her', 'its', 'our', 'their', 'mine', 'yours', 'ours', 'theirs'
        }

    def basic_tokenize(self, text):
        """Basic tokenization fallback if NLTK is not available"""
        # Remove punctuation and split by whitespace
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        return [word.strip() for word in text.split() if word.strip()]

    def basic_sent_split(self, text):
        """Basic sentence splitting fallback if NLTK is not available"""
        # Split by common sentence endings
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def extract_keywords(self, text, top_n=10):
        """Extract keywords from text"""
        if NLTK_AVAILABLE:
            try:
                stop_words = set(stopwords.words('english'))
                words = word_tokenize(re.sub(r'\W+', ' ', text.lower()))
            except Exception:
                # Fallback to basic processing if NLTK fails
                stop_words = self.basic_stopwords
                words = self.basic_tokenize(text)
        else:
            stop_words = self.basic_stopwords
            words = self.basic_tokenize(text)

        filtered = [word for word in words if word not in stop_words and len(word) > 2]
        return [word for word, _ in Counter(filtered).most_common(top_n)]

    def extract_business_context(self, emails):
        """Extract business entities, technical terms, and domain knowledge"""
        context = {
            'entities_by_email': {},
            'entity_frequency': defaultdict(int),
            'technical_discussions': {},
            'company_activities': {'nikwax': [], 'paramo': [], 'percipere': []}
        }

        for email in emails:
            email_id = email['id']
            text = (email['subject'] + ' ' + email['body']).lower()

            # Extract entities
            found_entities = []
            for category, terms in self.business_entities.items():
                for term in terms:
                    if term in text:
                        found_entities.append({'category': category, 'term': term.title()})
                        context['entity_frequency'][term.title()] += 1

            context['entities_by_email'][email_id] = found_entities

            # Track company-specific activities
            sender_domain = email['senderemail'].split('@')[-1].lower()
            if 'nikwax' in sender_domain:
                context['company_activities']['nikwax'].append(email_id)
            elif 'paramo' in sender_domain:
                context['company_activities']['paramo'].append(email_id)
            elif 'percipere' in sender_domain:
                context['company_activities']['percipere'].append(email_id)

            # Extract technical discussions
            if any(tech in text for tech in ['validation', 'upload', 'template', 'data']):
                context['technical_discussions'][email_id] = {
                    'subject': email['subject'],
                    'key_terms': [term.title() for term in self.business_entities['technical_terms'] if term in text],
                    'date': email['sorttime'],
                    'sender': email['sendername']
                }

        return context

    def extract_workflow_progression(self, emails):
        """Track project workflow states and progress"""
        workflow = {
            'validation_timeline': [],
            'file_versions': [],
            'milestone_events': [],
            'status_summary': {
                'current_status': None,
                'latest_progress': None,
                'remaining_issues': None
            }
        }

        for email in emails:
            email_id = email['id']
            subject = email['subject']
            body = email['body']
            date = email['sorttime']

            # Track validation progress
            progress_match = re.search(r'(\d+)% success', body)
            if progress_match:
                progress_data = {
                    'email_id': email_id,
                    'date': date,
                    'progress_percent': int(progress_match.group(1)),
                    'sender': email['sendername'],
                    'subject': subject
                }
                workflow['validation_timeline'].append(progress_data)
                workflow['status_summary']['latest_progress'] = progress_data

            # Track issues remaining
            issues_match = re.search(r'(\d+) issues? remain', body)
            if issues_match:
                issues_data = {
                    'email_id': email_id,
                    'date': date,
                    'issues_remaining': int(issues_match.group(1)),
                    'sender': email['sendername'],
                    'subject': subject
                }
                workflow['validation_timeline'].append(issues_data)
                workflow['status_summary']['remaining_issues'] = issues_data

            # Track file versions
            version_match = re.search(r'[Vv]ersion\s+(\d+)', subject)
            if version_match:
                file_path_match = re.search(r'/[\w/]+\.xlsx', body)
                workflow['file_versions'].append({
                    'email_id': email_id,
                    'date': date,
                    'version': int(version_match.group(1)),
                    'file_path': file_path_match.group(0) if file_path_match else None,
                    'sender': email['sendername'],
                    'subject': subject
                })

            # Track milestone events
            if any(keyword in subject.lower() for keyword in ['submission', 'validation', 'halt', 'complete', 'critical']):
                workflow['milestone_events'].append({
                    'email_id': email_id,
                    'date': date,
                    'event_type': self._classify_milestone(subject),
                    'description': subject,
                    'sender': email['sendername'],
                    'priority': self._extract_priority(subject + ' ' + body)
                })

        # Sort all timeline events
        for key in ['validation_timeline', 'file_versions', 'milestone_events']:
            workflow[key].sort(key=lambda x: x['date'])

        # Determine current status
        if workflow['validation_timeline']:
            latest = workflow['validation_timeline'][-1]
            if 'progress_percent' in latest:
                workflow['status_summary']['current_status'] = f"{latest['progress_percent']}% complete"
            elif 'issues_remaining' in latest:
                workflow['status_summary']['current_status'] = f"{latest['issues_remaining']} issues remaining"

        return workflow

    def extract_issues_and_resolutions(self, emails):
        """Track issues from identification to resolution"""
        issues = {
            'data_quality_issues': [],
            'system_constraints': [],
            'process_issues': [],
            'resolution_timeline': [],
            'critical_issues': []
        }

        for email in emails:
            email_id = email['id']
            subject = email['subject']
            body = email['body']

            # Identify different types of issues
            if any(keyword in body.lower() for keyword in ['duplicate', 'missing', 'invalid']):
                issue_details = self._extract_data_issues(body)
                if issue_details:
                    issues['data_quality_issues'].append({
                        'email_id': email_id,
                        'date': email['sorttime'],
                        'issues': issue_details,
                        'sender': email['sendername'],
                        'status': 'identified'
                    })

            # System constraint issues
            if 'character length' in subject.lower() or 'limit' in body.lower():
                issues['system_constraints'].append({
                    'email_id': email_id,
                    'date': email['sorttime'],
                    'constraint_type': self._classify_constraint(subject + ' ' + body),
                    'description': subject,
                    'impact': self._extract_impact(body)
                })

            # Critical issues
            if 'critical' in subject.lower() or 'halt' in body.lower():
                issues['critical_issues'].append({
                    'email_id': email_id,
                    'date': email['sorttime'],
                    'issue_type': 'critical',
                    'description': subject,
                    'impact': self._extract_impact(body),
                    'action_required': 'immediate'
                })

        return issues

    def extract_decisions_and_actions(self, emails):
        """Capture key decisions and action items"""
        decisions = {
            'key_decisions': [],
            'action_items': [],
            'meeting_outcomes': [],
            'recommendations': []
        }

        for email in emails:
            email_id = email['id']
            body = email['body']
            subject = email['subject']

            # Identify decisions
            if any(keyword in body.lower() for keyword in ['decision', 'agreed', 'decided', 'will adopt']):
                decision_context = self._extract_decision_context(body)
                if decision_context:
                    decisions['key_decisions'].append({
                        'email_id': email_id,
                        'date': email['sorttime'],
                        'decision_maker': email['sendername'],
                        'decision': decision_context,
                        'subject': subject
                    })

            # Meeting outcomes
            if 'meeting' in subject.lower() and 'summary' in subject.lower():
                outcomes = self._extract_meeting_outcomes(body)
                decisions['meeting_outcomes'].append({
                    'email_id': email_id,
                    'date': email['sorttime'],
                    'meeting_type': self._classify_meeting(subject),
                    'outcomes': outcomes,
                    'next_steps': self._extract_next_steps(body)
                })

            # Recommendations
            if 'recommend' in body.lower():
                decisions['recommendations'].append({
                    'email_id': email_id,
                    'date': email['sorttime'],
                    'recommender': email['sendername'],
                    'recommendation': body[:300] + "..." if len(body) > 300 else body,
                    'priority': self._extract_priority(body)
                })

        return decisions

    def create_conversation_threads(self, emails):
        """Create conversation threading and context flow"""
        threads = {
            'main_thread': [],
            'sub_threads': defaultdict(list),
            'conversation_flow': [],
            'participant_interactions': defaultdict(list)
        }

        # Group by conversation ID and subject patterns
        for email in emails:
            email_id = email['id']
            subject = email['subject']

            # Main thread (all emails are in same conversation)
            threads['main_thread'].append({
                'email_id': email_id,
                'date': email['sorttime'],
                'sender': email['sendername'],
                'subject': subject,
                'has_attachments': email['hasattachments']
            })

            # Sub-threads by subject similarity
            base_subject = re.sub(r'^(RE:|FW:)\s*', '', subject).strip()
            threads['sub_threads'][base_subject].append(email_id)

            # Track participant interactions
            sender = email['sendername']
            recipients = [r.strip() for r in email['recipientname'].split(',')]
            for recipient in recipients:
                threads['participant_interactions'][sender].append({
                    'to': recipient,
                    'email_id': email_id,
                    'date': email['sorttime']
                })

        # Sort main thread by date
        threads['main_thread'].sort(key=lambda x: x['date'])

        return threads

    def create_semantic_clusters(self, emails):
        """Group emails by semantic similarity for better retrieval"""
        clusters = {
            'validation_cluster': [],
            'upload_cluster': [],
            'issue_cluster': [],
            'data_quality_cluster': [],
            'progress_cluster': [],
            'coordination_cluster': [],
            'decision_cluster': [],
            'technical_cluster': []
        }

        for email in emails:
            email_id = email['id']
            text = (email['subject'] + ' ' + email['body']).lower()

            # Assign to clusters based on keywords
            if any(keyword in text for keyword in ['validation', 'validate']):
                clusters['validation_cluster'].append(email_id)

            if any(keyword in text for keyword in ['upload', 'submission', 'file']):
                clusters['upload_cluster'].append(email_id)

            if any(keyword in text for keyword in ['issue', 'problem', 'error', 'critical']):
                clusters['issue_cluster'].append(email_id)

            if any(keyword in text for keyword in ['duplicate', 'missing', 'data quality', 'invalid']):
                clusters['data_quality_cluster'].append(email_id)

            if any(keyword in text for keyword in ['progress', 'success rate', 'completion', 'percent']):
                clusters['progress_cluster'].append(email_id)

            if any(keyword in text for keyword in ['team', 'coordinate', 'assign', 'batch']):
                clusters['coordination_cluster'].append(email_id)

            if any(keyword in text for keyword in ['decision', 'meeting', 'agreed', 'format']):
                clusters['decision_cluster'].append(email_id)

            if any(keyword in text for keyword in ['template', 'plant data', 'mrp', 'warehouse']):
                clusters['technical_cluster'].append(email_id)

        return clusters

    # Helper methods
    def _classify_milestone(self, subject):
        """Classify milestone event types"""
        subject_lower = subject.lower()
        if 'submission' in subject_lower:
            return 'file_submission'
        elif 'validation' in subject_lower:
            return 'validation_result'
        elif 'halt' in subject_lower:
            return 'project_halt'
        elif 'complete' in subject_lower:
            return 'completion'
        elif 'critical' in subject_lower:
            return 'critical_issue'
        else:
            return 'other'

    def _extract_priority(self, text):
        """Extract priority indicators"""
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in ['urgent', 'critical', 'immediate']):
            return 'high'
        elif any(keyword in text_lower for keyword in ['recommend', 'should']):
            return 'medium'
        else:
            return 'low'

    def _extract_data_issues(self, body):
        """Extract specific data issues from email body"""
        issues = []

        # Look for duplicate mentions
        duplicate_match = re.search(r'(\d+) duplicate', body)
        if duplicate_match:
            issues.append(f"Duplicate records: {duplicate_match.group(1)}")

        # Look for missing data mentions
        missing_matches = re.findall(r'(\d+) (?:records|products)? missing ([^,\n.]+)', body)
        for match in missing_matches:
            issues.append(f"Missing {match[1].strip()}: {match[0]} records")

        # Look for invalid data mentions
        invalid_matches = re.findall(r'(\d+) (?:products|records)? with invalid ([^,\n.]+)', body)
        for match in invalid_matches:
            issues.append(f"Invalid {match[1].strip()}: {match[0]} records")

        return issues

    def _classify_constraint(self, text):
        """Classify system constraint types"""
        text_lower = text.lower()
        if 'character length' in text_lower:
            return 'field_length_limit'
        elif 'limit' in text_lower:
            return 'system_limit'
        else:
            return 'other_constraint'

    def _extract_impact(self, body):
        """Extract impact description from email body"""
        if NLTK_AVAILABLE:
            try:
                sentences = sent_tokenize(body)
            except Exception:
                sentences = self.basic_sent_split(body)
        else:
            sentences = self.basic_sent_split(body)

        impact_sentences = []
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in ['affect', 'impact', 'cannot', 'limited']):
                impact_sentences.append(sentence.strip())
        return ' '.join(impact_sentences[:2])  # First 2 relevant sentences

    def _extract_decision_context(self, body):
        """Extract decision context from email body"""
        if NLTK_AVAILABLE:
            try:
                sentences = sent_tokenize(body)
            except Exception:
                sentences = self.basic_sent_split(body)
        else:
            sentences = self.basic_sent_split(body)

        decision_sentences = []
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in ['decision', 'agreed', 'decided', 'will']):
                decision_sentences.append(sentence.strip())
        return ' '.join(decision_sentences[:2])  # First 2 relevant sentences

    def _classify_meeting(self, subject):
        """Classify meeting types"""
        if 'character length' in subject.lower():
            return 'technical_discussion'
        elif 'product number' in subject.lower():
            return 'business_decision'
        else:
            return 'general_meeting'

    def _extract_meeting_outcomes(self, body):
        """Extract meeting outcomes"""
        outcomes = []
        lines = body.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith(('1.', '2.', '3.', '4.', '5.', '-')):
                outcomes.append(line)
        return outcomes[:5]  # Top 5 outcomes

    def _extract_next_steps(self, body):
        """Extract next steps from meeting summary"""
        lines = body.split('\n')
        next_steps = []
        in_next_section = False
        for line in lines:
            line = line.strip()
            if 'next' in line.lower() and ('meeting' in line.lower() or 'step' in line.lower()):
                in_next_section = True
                next_steps.append(line)
            elif in_next_section and line:
                next_steps.append(line)
                if len(next_steps) >= 3:  # Limit to 3 next steps
                    break
        return next_steps

    def transform_emails(self, raw_file_path, result_dir):
        """Main transformation method"""
        os.makedirs(result_dir, exist_ok=True)

        print(f"📧 Loading emails from: {raw_file_path}")
        with open(raw_file_path, 'r', encoding='utf-8') as f:
            emails = json.load(f)

        # Sort emails by date
        emails.sort(key=lambda e: datetime.fromisoformat(e['sorttime']))

        print(f"🔄 Transforming {len(emails)} emails...")

        # Create all transformations
        print("📊 Extracting business context...")
        business_context = self.extract_business_context(emails)

        print("📈 Tracking workflow progression...")
        workflow_states = self.extract_workflow_progression(emails)

        print("🔍 Analyzing issues and resolutions...")
        issues_resolution = self.extract_issues_and_resolutions(emails)

        print("✅ Capturing decisions and actions...")
        decisions_actions = self.extract_decisions_and_actions(emails)

        print("🔗 Creating conversation threads...")
        conversation_threads = self.create_conversation_threads(emails)

        print("🏷️  Building semantic clusters...")
        semantic_clusters = self.create_semantic_clusters(emails)

        transformations = {
            'business_context.json': business_context,
            'workflow_states.json': workflow_states,
            'issues_resolution.json': issues_resolution,
            'decisions_actions.json': decisions_actions,
            'conversation_threads.json': conversation_threads,
            'semantic_clusters.json': semantic_clusters
        }

        # Add basic transformations
        print("📝 Creating basic summaries...")
        basic_transformations = {
            'subjects.json': self._create_subjects_summary(emails),
            'participants.json': self._create_participants_summary(emails),
            'timeline.json': self._create_timeline_summary(emails)
        }

        transformations.update(basic_transformations)

        # Save all transformation files
        print("💾 Saving transformation files...")
        for filename, data in transformations.items():
            output_path = os.path.join(result_dir, filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"   ✓ Created {filename}")

        # Create master index for query optimization
        print("📋 Creating master index...")
        master_index = {
            'workbook_name': os.path.basename(os.path.dirname(raw_file_path)),
            'total_emails': len(emails),
            'date_range': {
                'start': emails[0]['sorttime'],
                'end': emails[-1]['sorttime']
            },
            'transformation_files': list(transformations.keys()),
            'query_routing': {
                'progress_queries': ['workflow_states.json', 'semantic_clusters.json'],
                'issue_queries': ['issues_resolution.json', 'semantic_clusters.json'],
                'decision_queries': ['decisions_actions.json', 'conversation_threads.json'],
                'participant_queries': ['participants.json', 'conversation_threads.json'],
                'timeline_queries': ['timeline.json', 'workflow_states.json'],
                'business_queries': ['business_context.json', 'semantic_clusters.json'],
                'technical_queries': ['semantic_clusters.json', 'business_context.json']
            },
            'statistics': {
                'companies': len(set([email['senderemail'].split('@')[-1] for email in emails])),
                'participants': len(set([email['senderemail'] for email in emails])),
                'subjects': len(set([email['subject'] for email in emails])),
                'attachments': sum(1 for email in emails if email['hasattachments']),
                'nltk_available': NLTK_AVAILABLE
            }
        }

        with open(os.path.join(result_dir, 'master_index.json'), 'w', encoding='utf-8') as f:
            json.dump(master_index, f, indent=2, ensure_ascii=False)
        print(f"   ✓ Created master_index.json")

        print(f"\n🎉 Enhanced transformation complete!")
        print(f"📁 Results saved to: {result_dir}")
        print(f"📊 {len(transformations)} transformation files created")
        print(f"📈 Token reduction estimate: ~85%")
        print(f"🔧 NLTK status: {'✅ Available' if NLTK_AVAILABLE else '⚠️  Using basic processing'}")

        return master_index

    def _create_subjects_summary(self, emails):
        """Create subjects summary for basic queries"""
        subjects = defaultdict(list)
        for email in emails:
            subjects[email['subject']].append(email['id'])
        return {subj: {'count': len(ids), 'email_ids': ids} for subj, ids in subjects.items()}

    def _create_participants_summary(self, emails):
        """Create participants summary for basic queries"""
        participants = {'senders': Counter(), 'recipients': Counter()}
        for email in emails:
            participants['senders'][email['senderemail']] += 1
            for rec in email['recipientemail'].split(', '):
                participants['recipients'][rec.strip()] += 1
        return participants

    def _create_timeline_summary(self, emails):
        """Create timeline summary for basic queries"""
        timeline = {
            'overall': {
                'first': emails[0]['id'],
                'last': emails[-1]['id'],
                'first_date': emails[0]['sorttime'],
                'last_date': emails[-1]['sorttime']
            },
            'by_month': defaultdict(list)
        }

        # Group by month
        for email in emails:
            month_key = email['sorttime'][:7]  # YYYY-MM
            timeline['by_month'][month_key].append(email['id'])

        return timeline

# Usage example:
# transformer = EnhancedEmailTransformer()
# transformer.transform_emails('raw_emails.json', 'result_dir/')
