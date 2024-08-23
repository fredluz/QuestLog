from flask import render_template
from openai import OpenAI
import json
from models.quest import Quest
from models.task import Task
from models.journal_entry import JournalEntry

def generate_status():
    quests = Quest.query.all()
    tasks = Task.query.all()
    journal_entries = JournalEntry.query.order_by(JournalEntry.date.desc()).limit(5).all()

    # Generate a life overview using OpenAI
    life_overview = generate_life_overview(quests, tasks, journal_entries)

    return render_template('status.html', quests=quests, tasks=tasks, journal_entries=journal_entries, life_overview=life_overview)

def generate_life_overview(quests, tasks, journal_entries):
    quest_data = [{
        "title": quest.title, 
        "description": quest.get_current_description(),
        "tasks": [{"content": task.content, "completed": task.completed} for task in quest.tasks],
        "memos": [memo.content for memo in quest.memos]
    } for quest in quests]

    recent_entries = [{"content": entry.content, "date": entry.date.strftime('%Y-%m-%d %H:%M')} for entry in journal_entries]

    prompt = f"""Based on the user's quests, tasks, and recent journal entries, provide a comprehensive overview of their life situation, 
    including an extensive emotional status and psychological analysis. This should be similar to a status menu in an RPG, but with a deep 
    focus on the user's mental and emotional state.

    Quests: {json.dumps(quest_data)}
    Recent Journal Entries: {json.dumps(recent_entries)}

    Write an engaging summary of the user's current life situation, highlighting key stats, life areas, and their psychological state. 
    Write in a style that is reminiscent of Disco Elysium, Ernest Hemingway, and Ulysses from Fallout: New Vegas.
    Be creative with the key stats and life areas, drawing inspiration from RPGs but tailoring them to real-life situations and psychological states.
    Ensure the output is a valid JSON object.
    Format your response as a JSON object with the following structure:

    {{
        "overall_status": "An engaging overview of the user's current life situation. Modern myth.",
        "psychological_analysis": "A deep dive into the user's current emotional and psychological state, written in an engaging, literary style.",
        "key_stats": [
            {{"name": "Stat name", "value": "Stat value", "description": "Brief description"}},
            ...
        ],
        "life_areas": [
            {{"area": "Area name", "status": "Brief status description"}},
            ...
        ],
        "emotional_states": [
            {{"emotion": "Emotion name", "intensity": "Intensity value (1-10)", "description": "Brief description of the emotional state"}},
            ...
        ]
    }}
    """

    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[
                {"role": "system", "content": "You are an RPG storyteller biographer and psychologist that writes engaging life overviews based on quest logs and journal entries."},
                {"role": "user", "content": prompt}
            ],
        )

        # Capture the raw content of the response
        raw_content = response.choices[0].message.content
        print("Raw API Response:", raw_content)

        # Clean up the response by removing triple backticks and any "json" label
        if raw_content.startswith("```json"):
            raw_content = raw_content.lstrip("```json").rstrip("```").strip()
        elif raw_content.startswith("```"):
            raw_content = raw_content.lstrip("```").rstrip("```").strip()

        # Now safely load the cleaned JSON content
        parsed_response = json.loads(raw_content)
        
        return parsed_response

    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {str(e)}")
        print("Raw response content:", repr(raw_content))
        return {
            "overall_status": "Unable to generate overview at this time.",
            "psychological_analysis": "Unable to generate psychological analysis at this time.",
            "key_stats": [],
            "life_areas": [],
            "emotional_states": []
        }
    except Exception as e:
        print(f"Error generating life overview: {str(e)}")
        return {
            "overall_status": "Unable to generate overview at this time.",
            "psychological_analysis": "Unable to generate psychological analysis at this time.",
            "key_stats": [],
            "life_areas": [],
            "emotional_states": []
        }
