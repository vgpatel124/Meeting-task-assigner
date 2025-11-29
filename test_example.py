import os
import json
from main import MeetingTaskAssigner
from dotenv import load_dotenv

load_dotenv()


def test_with_sample_transcript():
    """Test the system with the sample meeting transcript from requirements."""

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: Please set GROQ_API_KEY environment variable")
        print("Get your free API key from: https://console.groq.com/keys")
        return

    print("Initializing Meeting Task Assigner with Groq...")
    assigner = MeetingTaskAssigner(api_key)

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

    print("\n" + "=" * 80)
    print("PROCESSING SAMPLE MEETING TRANSCRIPT")
    print("=" * 80)
    print(f"\nTranscript:\n{sample_transcript}\n")

    # Process the transcript
    result = assigner.process_transcript_only(
        transcript=sample_transcript,
        team_members=team_members,
        output_file="test_output.json"
    )

    print("\n" + assigner.format_output_table(result))

    print("\n" + "=" * 80)
    print("DETAILED JSON OUTPUT")
    print("=" * 80)
    print(json.dumps(result, indent=2))

    # Validate against expected output
    print("\n" + "=" * 80)
    print("VALIDATION")
    print("=" * 80)
    validate_results(result)


def validate_results(result):
    """Validate that the output matches expected structure and content."""

    expected_task_count = 5
    tasks = result.get('tasks', [])

    print(f"\n✓ Tasks extracted: {len(tasks)}")
    print(f"  Expected: {expected_task_count}")

    if len(tasks) >= expected_task_count - 1:  # Allow some flexibility
        print("  Status: PASS ✓")
    else:
        print("  Status: FAIL ✗")

    assignments = {task.get('assigned_to') for task in tasks}
    expected_assignees = {'Sakshi', 'Mohit', 'Arjun', 'Lata'}

    print(f"\n✓ Team members assigned: {assignments}")
    print(f"  Expected: {expected_assignees}")

    if assignments.intersection(expected_assignees):
        print("  Status: PASS ✓")
    else:
        print("  Status: FAIL ✗")

    priorities = {task.get('priority') for task in tasks}
    print(f"\n✓ Priority levels used: {priorities}")

    if 'Critical' in priorities or 'High' in priorities:
        print("  Status: PASS ✓")
    else:
        print("  Status: FAIL ✗")

    has_dependencies = any(task.get('dependencies') for task in tasks)
    print(f"\n✓ Dependencies identified: {has_dependencies}")

    if has_dependencies:
        print("  Status: PASS ✓")
    else:
        print("  Status: WARNING ⚠ (Dependencies expected)")

    print("\n" + "=" * 80)
    print("Validation Complete!")
    print("=" * 80)


def test_with_audio_file(audio_path: str):
    """Test the system with an actual audio file."""

    if not os.path.exists(audio_path):
        print(f"Audio file not found: {audio_path}")
        return

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: Please set GROQ_API_KEY environment variable")
        print("Get your free API key from: https://console.groq.com/keys")
        return

    assigner = MeetingTaskAssigner(api_key)

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

    print(f"\nProcessing audio file: {audio_path}")

    result = assigner.process_meeting(
        audio_file_path=audio_path,
        team_members=team_members,
        output_file="audio_test_output.json"
    )

    print(assigner.format_output_table(result))


if __name__ == "__main__":
    test_with_sample_transcript()

