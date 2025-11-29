# Meeting Task Assignment System

Stop manually tracking who needs to do what after meetings. This tool listens to your meeting recordings and automatically figures out the tasks and who should handle them.

## What does it do?

You record a team meeting. The system:
- Converts the audio to text
- Picks out all the tasks mentioned
- Assigns them to the right people based on their skills
- Figures out priorities and deadlines
- Gives you a clean list to work with

That's it. No more "wait, who was supposed to do that?" moments.

## Getting Started

### You'll need:
- Python 3.8 or newer
- A Groq API key (it's free - get one at https://console.groq.com/keys)
- Your meeting recording (.mp3, .wav, or .m4a)
- A simple list of your team members and what they're good at

### Installation

```bash
# Install the required packages
pip install groq python-dotenv

# Optional: if you want the web interface
pip install streamlit pandas
```

Create a file called `.env` and add your API key:
```
GROQ_API_KEY=your_key_here
```

### Your Team File

Make a `team_members.json` file. Here's the format:

```json
[
  {
    "name": "Alex",
    "role": "Frontend Dev",
    "skills": "React, JavaScript, CSS"
  },
  {
    "name": "Sam",
    "role": "Backend Dev",
    "skills": "Python, APIs, Database"
  }
]
```

Just name, role, and skills. Nothing fancy.

## How to Use It

### Web Interface
```bash
streamlit run app.py
```

Upload your files through the browser. Click a button. Done.

### For Developers
```python
from main import MeetingTaskAssigner

assigner = MeetingTaskAssigner("your-api-key")
result = assigner.process_meeting(
    audio_file_path="meeting.mp3",
    team_members=team_data
)
```

## What You Get

The output is a JSON file that looks like this:

```json
{
  "meeting_summary": "Quick overview of what was discussed",
  "tasks": [
    {
      "task_id": 1,
      "title": "Fix the login bug",
      "description": "Users can't log in on mobile",
      "assigned_to": "Alex",
      "deadline": "End of week",
      "priority": "High",
      "dependencies": null,
      "reasoning": "Frontend issue, Alex handles mobile bugs"
    }
  ]
}
```

You also get a nice table printed to the console that's easier to read at a glance.

## Testing Without Audio

Don't have a meeting recording yet? Run this:

```bash
python test_example.py
```

It processes a sample transcript so you can see how everything works.

## Common Issues

**"GROQ_API_KEY not found"**  
You forgot to make the .env file or it's in the wrong folder.

**Tasks aren't getting assigned correctly**  
Check your team_members.json. Are the skills detailed enough? Did you spell names consistently?

**Audio transcription is garbage**  
Your audio quality probably isn't great. Try recording closer to the mic or in a quieter room.

**"Module not found" errors**  
Run `pip install -r requirements.txt` again. Or install the specific missing package.

## File Structure

```
meeting-task-assigner/
├── main.py              # Does the actual work
├── app.py               # Web interface (optional)
├── test_example.py      # Try it without real audio
├── requirements.txt     # What to install
├── .env                 # Your API key goes here
└── team_members.json    # Your team info
```

## How It Works (Technical Stuff)

1. Transcription: Uses Groq's Whisper model to convert speech to text (external API - allowed per project requirements)
2. Task Identification: Custom keyword matching and pattern recognition
    - Looks for action words (fix, create, update, etc.)
    - Identifies task-related phrases (need to, should, must, etc.)
3. Assignment Logic: 100% custom rule-based system
    - Checks for explicit name mentions first
    - Scores team members based on skill keywords in task description
    - Matches task types to roles (frontend, backend, QA, etc.)
    - Assigns to highest scoring team member
4. Priority & Deadlines: Pattern matching on keywords
    - Critical: "urgent", "blocking", "asap"
    - Deadlines: "by tomorrow", "end of week", etc.
5. Output: Structured JSON with all the details


## Limitations

- Only works in English right now
- Doesn't identify speakers (can't tell who said what, just what was said)
- Works best with structured meetings where tasks are clearly discussed
- Won't catch very subtle or implied tasks
- Needs decent audio quality to transcribe properly
