import streamlit as st
import json
import os
from main import MeetingTaskAssigner
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

st.set_page_config(
    page_title="Meeting Task Assigner",
    layout="wide"
)

# Initialize session state
if 'result' not in st.session_state:
    st.session_state.result = None


def main():
    st.title("Meeting Task Assignment System")
    st.divider()

    with st.sidebar:
        st.header("Configuration")

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            api_key = st.text_input(
                "Groq API Key",
                type="password",
                help="Get your free API key from https://console.groq.com/keys"
            )
        else:
            st.success("API Key loaded from .env")
            api_key_display = api_key[:8] + "..." + api_key[-4:]
            st.code(api_key_display)

        st.divider()
        st.markdown("###Instructions")
        st.markdown("""
        1. Upload audio file (.wav, .mp3, .m4a)
        2. Add team members or upload JSON
        3. Click 'Process Meeting'
        4. Download results
        """)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("Input")

        st.subheader("1. Upload Audio File")
        audio_file = st.file_uploader(
            "Choose an audio file",
            type=['wav', 'mp3', 'm4a'],
            help="Upload your meeting recording"
        )

        if audio_file:
            st.success(f"File loaded: {audio_file.name}")
            st.audio(audio_file)

        st.divider()

        st.subheader("2. Team Members")

        input_method = st.radio(
            "Choose input method:",
            ["Upload JSON file", "Manual entry"]
        )

        team_members = []

        if input_method == "Upload JSON file":
            team_file = st.file_uploader(
                "Upload team members JSON",
                type=['json'],
                help="JSON file with team member information"
            )

            if team_file:
                try:
                    team_members = json.load(team_file)
                    st.success(f"Loaded {len(team_members)} team members")

                    # Display team members
                    df = pd.DataFrame(team_members)
                    st.dataframe(df, use_container_width=True)

                except json.JSONDecodeError:
                    st.error("Invalid JSON format")

        else:
            st.markdown("Add team members one by one:")


            if 'team_members_manual' not in st.session_state:
                st.session_state.team_members_manual = []

            with st.form("add_member_form"):
                col_a, col_b = st.columns(2)
                with col_a:
                    name = st.text_input("Name")
                    role = st.text_input("Role")
                with col_b:
                    skills = st.text_area("Skills (comma-separated)", height=100)

                submitted = st.form_submit_button("➕ Add Team Member")

                if submitted and name and role and skills:
                    member = {
                        "name": name,
                        "role": role,
                        "skills": skills
                    }
                    st.session_state.team_members_manual.append(member)
                    st.success(f"Added {name}")


            if st.session_state.team_members_manual:
                st.markdown("**Added Members:**")
                for i, member in enumerate(st.session_state.team_members_manual):
                    col_x, col_y = st.columns([5, 1])
                    with col_x:
                        st.text(f"{member['name']} - {member['role']}")
                    with col_y:
                        if st.button("❌", key=f"remove_{i}"):
                            st.session_state.team_members_manual.pop(i)
                            st.rerun()

                team_members = st.session_state.team_members_manual


            st.divider()
            st.markdown("**Or download a template:**")
            template = [
                {
                    "name": "John Doe",
                    "role": "Software Engineer",
                    "skills": "Python, APIs, Database"
                }
            ]
            st.download_button(
                "Download JSON Template",
                data=json.dumps(template, indent=2),
                file_name="team_members_template.json",
                mime="application/json"
            )

    with col2:
        st.header("Output")

        # Process button
        if st.button("Process Meeting", type="primary", use_container_width=True):
            if not api_key:
                st.error("Please provide a Groq API key")
            elif not audio_file:
                st.error("Please upload an audio file")
            elif not team_members:
                st.error("Please add team members")
            else:
                with st.spinner("Processing meeting... This may take a minute."):
                    try:
                        # Save audio file temporarily
                        audio_path = f"temp_{audio_file.name}"
                        with open(audio_path, "wb") as f:
                            f.write(audio_file.getbuffer())

                        # Initialize assigner
                        assigner = MeetingTaskAssigner(api_key)

                        # Process meeting
                        result = assigner.process_meeting(
                            audio_file_path=audio_path,
                            team_members=team_members,
                            output_file="web_output.json"
                        )

                        st.session_state.result = result

                        # Clean up temp file
                        os.remove(audio_path)

                        st.success("Meeting processed successfully!")

                    except Exception as e:
                        st.error(f"Error: {str(e)}")

        if st.session_state.result:
            result = st.session_state.result

            st.divider()

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Total Tasks", len(result.get('tasks', [])))
            with col_b:
                assigned = len([t for t in result.get('tasks', []) if t.get('assigned_to')])
                st.metric("Assigned", assigned)
            with col_c:
                st.metric("Unassigned", len(result.get('unassigned_tasks', [])))

            st.divider()

            if result.get('meeting_summary'):
                st.subheader("Meeting Summary")
                st.info(result['meeting_summary'])

            st.subheader("Identified Tasks")

            tasks = result.get('tasks', [])
            if tasks:
                task_data = []
                for task in tasks:
                    task_data.append({
                        "ID": task.get('task_id', ''),
                        "Title": task.get('title', ''),
                        "Assigned To": task.get('assigned_to', 'Unassigned'),
                        "Deadline": task.get('deadline', 'Not set'),
                        "Priority": task.get('priority', 'Medium'),
                    })

                df = pd.DataFrame(task_data)
                st.dataframe(df, use_container_width=True)

                st.subheader("Task Details")
                for task in tasks:
                    with st.expander(f"Task #{task.get('task_id')}: {task.get('title')}"):
                        st.markdown(f"**Description:** {task.get('description', 'N/A')}")
                        st.markdown(f"**Assigned To:** {task.get('assigned_to', 'Unassigned')}")
                        st.markdown(f"**Deadline:** {task.get('deadline', 'Not set')}")
                        st.markdown(f"**Priority:** {task.get('priority', 'Medium')}")

                        if task.get('dependencies'):
                            st.markdown(f"**Dependencies:** Task #{', Task #'.join(map(str, task['dependencies']))}")

                        if task.get('reasoning'):
                            st.markdown(f"**Reasoning:** {task.get('reasoning')}")

                        if task.get('context'):
                            st.markdown(f"**Context:** {task.get('context')}")

            if result.get('unassigned_tasks'):
                st.subheader("Unassigned Tasks")
                for utask in result['unassigned_tasks']:
                    st.warning(f"**{utask.get('description')}**\nReason: {utask.get('reason')}")

            st.divider()
            col_x, col_y = st.columns(2)

            with col_x:
                st.download_button(
                    "Download JSON",
                    data=json.dumps(result, indent=2),
                    file_name="task_assignments.json",
                    mime="application/json",
                    use_container_width=True
                )

            with col_y:
                if tasks:
                    csv = pd.DataFrame([{
                        "Task ID": t.get('task_id'),
                        "Title": t.get('title'),
                        "Description": t.get('description'),
                        "Assigned To": t.get('assigned_to'),
                        "Deadline": t.get('deadline'),
                        "Priority": t.get('priority'),
                        "Reasoning": t.get('reasoning')
                    } for t in tasks]).to_csv(index=False)

                    st.download_button(
                        "Download CSV",
                        data=csv,
                        file_name="task_assignments.csv",
                        mime="text/csv",
                        use_container_width=True
                    )


if __name__ == "__main__":
    main()