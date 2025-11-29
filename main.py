import os
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from groq import Groq
from collections import defaultdict


class MeetingTaskAssigner:
    """
    A system that processes meeting transcripts and automatically assigns tasks
    to team members using CUSTOM LOGIC (no pre-trained models for classification).

    Uses Groq ONLY for Speech-to-Text (allowed per requirements).
    Task identification and assignment uses custom rule-based logic.
    """

    def __init__(self, api_key: str):
        """Initialize with Groq API key (for Speech-to-Text only)."""
        self.api_key = api_key
        self.client = Groq(api_key=api_key)

        # Task-related keywords for identification
        self.task_keywords = [
            'need to', 'needs to', 'should', 'must', 'have to', 'got to',
            'can you', 'could you', 'would you', 'please',
            'fix', 'create', 'build', 'design', 'develop', 'write', 'update',
            'implement', 'review', 'test', 'deploy', 'optimize', 'refactor',
            'debug', 'investigate', 'research', 'document', 'prepare'
        ]

        # Priority keywords
        self.priority_keywords = {
            'critical': ['critical', 'urgent', 'asap', 'emergency', 'blocking', 'blocker'],
            'high': ['high priority', 'important', 'soon', 'quickly', 'high'],
            'low': ['low priority', 'whenever', 'eventually', 'nice to have', 'low'],
            'medium': ['medium', 'normal', 'regular']
        }

        # Deadline patterns - order matters (more specific first)
        self.deadline_patterns = [
            (r'by (tomorrow|tmrw)', 'Tomorrow'),
            (r'(tomorrow|tmrw)', 'Tomorrow'),
            (r'by (today|tonight)', 'Today'),
            (r'end of (this )?week', 'End of this week'),
            (r'by (the )?weekend', 'Weekend'),
            (r'finish by (the )?weekend', 'Weekend'),
            (r'by (friday|fri)(\s+evening)?', 'Friday'),
            (r'(friday|fri)(\s+evening)?', 'Friday'),
            (r'by (monday|mon)', 'Monday'),
            (r'by (tuesday|tue)', 'Tuesday'),
            (r'by (wednesday|wed)', 'Wednesday'),
            (r'by (thursday|thu)', 'Thursday'),
            (r'by (saturday|sat)', 'Saturday'),
            (r'by (sunday|sun)', 'Sunday'),
            (r'on (monday|mon)', 'Monday'),
            (r'on (tuesday|tue)', 'Tuesday'),
            (r'on (wednesday|wed)', 'Wednesday'),
            (r'on (thursday|thu)', 'Thursday'),
            (r'on (friday|fri)', 'Friday'),
            (r'on (saturday|sat)', 'Saturday'),
            (r'on (sunday|sun)', 'Sunday'),
            (r'(start|begin|starting).*?(monday|mon)', 'Monday'),
            (r'(start|begin|starting).*?(tuesday|tue)', 'Tuesday'),
            (r'(start|begin|starting).*?(wednesday|wed)', 'Wednesday'),
            (r'(start|begin|starting).*?(thursday|thu)', 'Thursday'),
            (r'(start|begin|starting).*?(friday|fri)', 'Friday'),
            (r'next (week|monday|tuesday|wednesday|thursday|friday|weekend)', 'Next week'),
            (r'in (\d+) days?', lambda m: f'In {m[1]} days'),
            (r'for (figma|the|new|notification)', None),  # Skip these matches
        ]

    def transcribe_audio(self, audio_file_path: str) -> str:
        """
        Convert audio to text using Groq Whisper API.
        This is ALLOWED per project requirements.
        """
        print(f"Transcribing audio file: {audio_file_path}")

        with open(audio_file_path, "rb") as audio_file:
            transcription = self.client.audio.transcriptions.create(
                file=(audio_file_path, audio_file.read()),
                model="whisper-large-v3-turbo",
                response_format="json",
                language="en",
                temperature=0.0
            )

        print("Transcription completed!")
        return transcription.text

    def extract_tasks_from_transcript(
            self,
            transcript: str,
            team_members: List[Dict]
    ) -> Dict:
        """
        Extract and assign tasks using CUSTOM RULE-BASED LOGIC.
        No external AI models for classification - all custom logic.
        """
        print("Analyzing transcript with custom logic...")

        sentences = self._split_into_sentences(transcript)

        potential_tasks = self._identify_tasks(sentences)

        tasks = []
        task_id = 1

        for i, task_info in enumerate(potential_tasks):
            description = self._extract_task_description(task_info['sentence'])

            assigned_to = self._find_explicit_assignment(task_info['sentence'], team_members)

            if not assigned_to:
                assigned_to = self._assign_based_on_skills(description, team_members)

            deadline = self._extract_deadline(task_info['sentence'])

            if not deadline:
                if i > 0:
                    prev_sentence = sentences[max(0, task_info['sentence_index'] - 1)]
                    deadline = self._extract_deadline(prev_sentence)

                if not deadline and task_info['sentence_index'] < len(sentences) - 1:
                    next_sentence = sentences[task_info['sentence_index'] + 1]
                    deadline = self._extract_deadline(next_sentence)

            priority = self._determine_priority(task_info['sentence'])

            task = {
                'task_id': task_id,
                'title': self._generate_title(description),
                'description': description,
                'assigned_to': assigned_to['name'] if assigned_to else None,
                'deadline': deadline,
                'priority': priority,
                'dependencies': None,
                'reasoning': assigned_to['reasoning'] if assigned_to else 'No suitable team member found',
                'context': task_info['sentence']
            }

            tasks.append(task)
            task_id += 1

        tasks = self._identify_dependencies(tasks)

        unassigned = [
            {
                'description': t['description'],
                'reason': 'No team member with matching skills found'
            }
            for t in tasks if not t['assigned_to']
        ]

        assigned_tasks = [t for t in tasks if t['assigned_to']]

        result = {
            'meeting_summary': self._generate_summary(transcript, len(tasks)),
            'tasks': assigned_tasks,
            'unassigned_tasks': unassigned
        }

        print(f"Extracted {len(assigned_tasks)} tasks using custom logic")
        return result

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    def _identify_tasks(self, sentences: List[str]) -> List[Dict]:
        """Identify sentences that likely contain tasks using keyword matching."""
        tasks = []

        for idx, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()

            for keyword in self.task_keywords:
                if keyword in sentence_lower:
                    tasks.append({
                        'sentence': sentence,
                        'sentence_index': idx,
                        'keyword': keyword
                    })
                    break  # One match per sentence is enough

        return tasks

    def _extract_task_description(self, sentence: str) -> str:
        """Extract the actual task description from sentence."""
        sentence = sentence.strip()

        match = re.search(r'(need to|should|must|have to|can you|could you|please)\s+(.+)',
                          sentence, re.IGNORECASE)
        if match:
            return match.group(2).strip()

        return sentence

    def _find_explicit_assignment(self, sentence: str, team_members: List[Dict]) -> Optional[Dict]:
        """Find if someone is explicitly mentioned in the sentence."""
        sentence_lower = sentence.lower()

        for member in team_members:
            name_lower = member['name'].lower()

            pattern = r'\b' + re.escape(name_lower) + r'\b'

            if re.search(pattern, sentence_lower):
                return {
                    'name': member['name'],
                    'reasoning': f'Explicitly mentioned in discussion'
                }

        return None

    def _assign_based_on_skills(self, description: str, team_members: List[Dict]) -> Optional[Dict]:
        """Assign task based on skill matching - CUSTOM LOGIC."""
        description_lower = description.lower()

        scores = []

        for member in team_members:
            score = 0
            matched_skills = []

            skills = member['skills'].lower().split(',')
            for skill in skills:
                skill = skill.strip()
                if skill and skill in description_lower:
                    score += 2
                    matched_skills.append(skill)

            role_lower = member['role'].lower()
            role_keywords = role_lower.split()
            for keyword in role_keywords:
                if keyword in description_lower:
                    score += 1

            role_task_mapping = {
                'frontend': ['ui', 'interface', 'button', 'screen', 'page', 'css', 'react', 'design'],
                'backend': ['database', 'api', 'server', 'endpoint', 'performance', 'optimization'],
                'designer': ['design', 'mockup', 'wireframe', 'prototype', 'ux', 'ui'],
                'qa': ['test', 'testing', 'quality', 'bug', 'validation', 'automation'],
                'devops': ['deploy', 'deployment', 'infrastructure', 'ci/cd', 'docker']
            }

            for role_type, keywords in role_task_mapping.items():
                if role_type in role_lower:
                    for keyword in keywords:
                        if keyword in description_lower:
                            score += 1.5

            if score > 0:
                scores.append({
                    'member': member,
                    'score': score,
                    'matched_skills': matched_skills
                })

        if scores:
            best_match = max(scores, key=lambda x: x['score'])
            reasoning = f"Best match based on skills: {', '.join(best_match['matched_skills']) if best_match['matched_skills'] else member['role']}"

            return {
                'name': best_match['member']['name'],
                'reasoning': reasoning
            }

        return None

    def _extract_deadline(self, sentence: str) -> Optional[str]:
        """Extract deadline from sentence using pattern matching."""
        sentence_lower = sentence.lower()

        for pattern, deadline_text in self.deadline_patterns:
            if deadline_text is None:  # Skip pattern
                continue

            match = re.search(pattern, sentence_lower)
            if match:
                if callable(deadline_text):
                    return deadline_text(match.groups())
                return deadline_text

        days = {
            'monday': 'Monday', 'mon': 'Monday',
            'tuesday': 'Tuesday', 'tue': 'Tuesday',
            'wednesday': 'Wednesday', 'wed': 'Wednesday',
            'thursday': 'Thursday', 'thu': 'Thursday',
            'friday': 'Friday', 'fri': 'Friday',
            'saturday': 'Saturday', 'sat': 'Saturday',
            'sunday': 'Sunday', 'sun': 'Sunday',
        }

        for day_key, day_value in days.items():
            if re.search(rf'\b{day_key}\b', sentence_lower):
                return day_value

        if any(word in sentence_lower for word in ['asap', 'urgent', 'immediately', 'now']):
            return 'ASAP'

        if 'next sprint' in sentence_lower or 'next iteration' in sentence_lower:
            return 'Next sprint'

        return None

    def _determine_priority(self, sentence: str) -> str:
        """Determine priority based on keywords."""
        sentence_lower = sentence.lower()

        for priority, keywords in self.priority_keywords.items():
            for keyword in keywords:
                if keyword in sentence_lower:
                    return priority.capitalize()

        return 'Medium'

    def _generate_title(self, description: str) -> str:
        """Generate a short title from description."""
        words = description.split()
        title = ' '.join(words[:6])
        if len(title) > 50:
            title = title[:47] + '...'
        return title

    def _identify_dependencies(self, tasks: List[Dict]) -> List[Dict]:
        """Identify task dependencies using keyword matching."""
        dependency_keywords = ['depends on', 'after', 'once', 'when', 'first']

        for i, task in enumerate(tasks):
            context_lower = task['context'].lower()

            for keyword in dependency_keywords:
                if keyword in context_lower:
                    if i > 0:
                        task['dependencies'] = [tasks[i - 1]['task_id']]
                    break

        return tasks

    def _generate_summary(self, transcript: str, task_count: int) -> str:
        """Generate a simple meeting summary."""
        sentences = self._split_into_sentences(transcript)

        return f"Meeting discussion with {task_count} tasks identified from {len(sentences)} discussion points"

    def process_meeting(
            self,
            audio_file_path: str,
            team_members: List[Dict],
            output_file: str = "task_assignments.json"
    ) -> Dict:
        """Complete pipeline: transcribe audio and extract tasks."""
        transcript = self.transcribe_audio(audio_file_path)

        result = self.extract_tasks_from_transcript(transcript, team_members)

        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\nResults saved to: {output_file}")
        return result

    def process_transcript_only(
            self,
            transcript: str,
            team_members: List[Dict],
            output_file: str = "task_assignments.json"
    ) -> Dict:
        """Process an existing transcript (skip audio transcription)."""
        result = self.extract_tasks_from_transcript(transcript, team_members)

        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\nResults saved to: {output_file}")
        return result

    def format_output_table(self, result: Dict) -> str:
        """Format the result as a readable table."""
        output = "\n" + "=" * 100 + "\n"
        output += "MEETING TASK ASSIGNMENTS\n"
        output += "=" * 100 + "\n\n"

        if result.get('meeting_summary'):
            output += f"Summary: {result['meeting_summary']}\n\n"

        output += f"{'#':<4} {'Task':<30} {'Assigned To':<15} {'Deadline':<15} {'Priority':<10} {'Dependencies':<15}\n"
        output += "-" * 100 + "\n"

        for task in result.get('tasks', []):
            task_id = task.get('task_id', '-')
            title = task.get('title', 'N/A')[:28]
            assigned = task.get('assigned_to', 'Unassigned')[:13]
            deadline = task.get('deadline', 'Not set')[:13] if task.get('deadline') else 'Not set'
            priority = task.get('priority', 'Medium')[:8]
            deps = ', '.join(map(str, task.get('dependencies', []))) if task.get('dependencies') else '—'

            output += f"{task_id:<4} {title:<30} {assigned:<15} {deadline:<15} {priority:<10} {deps:<15}\n"

            if task.get('description'):
                output += f"     Description: {task['description']}\n"
            if task.get('reasoning'):
                output += f"     Reasoning: {task['reasoning']}\n"
            output += "\n"

        if result.get('unassigned_tasks'):
            output += "\nUNASSIGNED TASKS:\n"
            output += "-" * 100 + "\n"
            for utask in result['unassigned_tasks']:
                output += f"- {utask.get('description', 'N/A')}\n"
                output += f"  Reason: {utask.get('reason', 'Unknown')}\n\n"

        output += "=" * 100 + "\n"
        return output


# Example usage
if __name__ == "__main__":
    API_KEY = ""
    assigner = MeetingTaskAssigner(API_KEY)

    team_members = [
        {
            "name": "Sakshi",
            "role": "Frontend Developer",
            "skills": "React, JavaScript, UI bugs"
        },
        {
            "name": "Mohit",
            "role": "Backend Engineer",
            "skills": "Database, APIs, Performance optimization"
        },
        {
            "name": "Arjun",
            "role": "UI/UX Designer",
            "skills": "Figma, User flows, Mobile design"
        },
        {
            "name": "Lata",
            "role": "QA Engineer",
            "skills": "Testing, Automation, Quality assurance"
        }
    ]

    sample_transcript = """
    Hi everyone, let's discuss this week's priorities.
    Sakshi, we need someone to fix the critical login bug that users reported yesterday.
    This needs to be done by tomorrow evening since it's blocking users.
    Also, the database performance is really slow, Mohit you're good with backend
    optimization right?
    We should tackle this by end of this week, it's affecting the user experience.
    And we need to update the API documentation before Friday's release - this is high
    priority.
    Oh, and someone should design the new onboarding screens for the next sprint.
    Arjun, didn't you work on UI designs last month? This can wait until next Monday.
    One more thing - we need to write unit tests for the payment module.
    This depends on the login bug fix being completed first, so let's plan this for
    Wednesday.
    """

    result = assigner.process_transcript_only(
        transcript=sample_transcript,
        team_members=team_members,
        output_file="task_assignments.json"
    )

    print(assigner.format_output_table(result))