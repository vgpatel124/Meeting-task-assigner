import os
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from groq import Groq


class MeetingTaskAssigner:
    """
    A system that processes meeting transcripts and automatically assigns tasks
    to team members based on content analysis using Groq API.
    """

    def __init__(self, api_key: str):
        """Initialize with Groq API key."""
        self.api_key = api_key
        self.client = Groq(api_key=api_key)

    def transcribe_audio(self, audio_file_path: str) -> str:
        """
        Convert audio file to text using Groq Whisper API.

        Args:
            audio_file_path: Path to audio file (.wav, .mp3, .m4a)

        Returns:
            Transcribed text
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
        Extract and assign tasks from meeting transcript using custom logic.

        Args:
            transcript: Meeting transcript text
            team_members: List of team member dictionaries with name, role, skills

        Returns:
            Structured task assignment data
        """
        print("Analyzing transcript and extracting tasks...")

        team_context = self._build_team_context(team_members)

        system_prompt = self._get_system_prompt()
        user_prompt = self._build_user_prompt(transcript, team_context)

        chat_completion = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.3-70b-versatile",  # Best model for complex reasoning
            temperature=0.3,
            max_tokens=4096,
            response_format={"type": "json_object"}
        )

        result = json.loads(chat_completion.choices[0].message.content)

        result = self._validate_and_enhance(result, team_members)

        print(f"Extracted {len(result.get('tasks', []))} tasks")
        return result

    def _get_system_prompt(self) -> str:
        """Get the system prompt for task extraction."""
        return """You are an intelligent meeting assistant that analyzes meeting transcripts to identify tasks, prioritize them, and assign them to appropriate team members.

Your responsibilities:

1. TASK IDENTIFICATION
   - Extract all actionable items from the meeting
   - Identify explicit tasks (directly stated) and implicit tasks (suggested)
   - Capture full context of each task
   - Distinguish tasks from general discussion

2. TASK ANALYSIS
   - Determine deadlines from phrases like "by tomorrow", "end of week", "next Monday"
   - Assess priority: Critical (blocking/urgent), High (important deadlines), Medium (scheduled work), Low (nice-to-have)
   - Identify dependencies between tasks
   - Note blockers or special conditions

3. TASK ASSIGNMENT
   - Match tasks based on:
     * Explicit mentions (e.g., "Sakshi, can you...")
     * Role alignment (frontend tasks → frontend developer)
     * Skill matching (database work → backend with database skills)
     * Past experience mentioned
   - Provide clear reasoning for assignments

4. IMPORTANT RULES
   - Be conservative: only extract clear, actionable tasks
   - Don't hallucinate information not in transcript
   - If uncertain about assignment, note it in reasoning
   - Preserve context and nuance

Return a JSON object with this exact structure:
{
  "meeting_summary": "Brief overview",
  "tasks": [
    {
      "task_id": 1,
      "title": "Short descriptive title",
      "description": "Detailed description",
      "assigned_to": "Team member name or null",
      "deadline": "Parsed deadline or null",
      "priority": "Critical|High|Medium|Low",
      "dependencies": [task_ids] or null,
      "reasoning": "Assignment reasoning",
      "context": "Additional context/blockers"
    }
  ],
  "unassigned_tasks": [
    {
      "description": "Task description",
      "reason": "Why it couldn't be assigned"
    }
  ]
}"""

    def _build_team_context(self, team_members: List[Dict]) -> str:
        """Build a formatted string of team member information."""
        context = "TEAM MEMBERS:\n"
        for member in team_members:
            context += f"- Name: {member['name']}\n"
            context += f"  Role: {member['role']}\n"
            context += f"  Skills: {member['skills']}\n"
        return context

    def _build_user_prompt(self, transcript: str, team_context: str) -> str:
        """Build the user prompt with transcript and team info."""
        return f"""Analyze this meeting transcript and extract all tasks with assignments.

{team_context}

MEETING TRANSCRIPT:
{transcript}

Extract all tasks, assign them to appropriate team members, and return the structured JSON output."""

    def _validate_and_enhance(
            self,
            result: Dict,
            team_members: List[Dict]
    ) -> Dict:
        """Validate and enhance the extracted task data."""

        if 'tasks' not in result:
            result['tasks'] = []
        if 'unassigned_tasks' not in result:
            result['unassigned_tasks'] = []

        valid_names = {member['name'] for member in team_members}

        for task in result['tasks']:
            if 'task_id' not in task:
                task['task_id'] = result['tasks'].index(task) + 1

            if task.get('assigned_to') and task['assigned_to'] not in valid_names:
                task['assigned_to'] = self._find_closest_name(
                    task['assigned_to'],
                    valid_names
                )

            if 'priority' in task:
                task['priority'] = task['priority'].capitalize()

            task.setdefault('title', 'Untitled Task')
            task.setdefault('description', '')
            task.setdefault('deadline', None)
            task.setdefault('priority', 'Medium')
            task.setdefault('dependencies', None)
            task.setdefault('reasoning', '')
            task.setdefault('context', '')

        return result

    def _find_closest_name(self, name: str, valid_names: set) -> Optional[str]:
        """Find the closest matching name from valid names."""
        name_lower = name.lower()
        for valid_name in valid_names:
            if name_lower in valid_name.lower() or valid_name.lower() in name_lower:
                return valid_name
        return None

    def process_meeting(
            self,
            audio_file_path: str,
            team_members: List[Dict],
            output_file: str = "task_assignments.json"
    ) -> Dict:
        """
        Complete pipeline: transcribe audio and extract tasks.

        Args:
            audio_file_path: Path to audio file
            team_members: List of team member info
            output_file: Path to save output JSON

        Returns:
            Task assignment data
        """
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
        """
        Process an existing transcript (skip audio transcription).

        Args:
            transcript: Meeting transcript text
            team_members: List of team member info
            output_file: Path to save output JSON

        Returns:
            Task assignment data
        """
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
            if task.get('context'):
                output += f"     Context: {task['context']}\n"
            output += "\n"

        if result.get('unassigned_tasks'):
            output += "\nUNASSIGNED TASKS:\n"
            output += "-" * 100 + "\n"
            for utask in result['unassigned_tasks']:
                output += f"- {utask.get('description', 'N/A')}\n"
                output += f"  Reason: {utask.get('reason', 'Unknown')}\n\n"

        output += "=" * 100 + "\n"
        return output


if __name__ == "__main__":
    API_KEY = "Your API key"
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