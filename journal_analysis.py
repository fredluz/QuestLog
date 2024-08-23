from openai import OpenAI
import json
from dateutil.parser import parse as parse_date
from sqlalchemy.exc import SQLAlchemyError
from models.db import db
from models.quest import Quest


def analyze_entry(entry):
    quests = Quest.query.all()
    quest_data = [{
        "title": quest.title, 
        "description": [desc.content for desc in quest.description],
        "tasks": [task.content for task in quest.tasks],
        "memos": [memo.content for memo in quest.memos]
    } for quest in quests]    
    for quest in quest_data:
        assert isinstance(quest['tasks'], list), f"Expected list, got {type(quest['tasks'])}"
        assert isinstance(quest['memos'], list), f"Expected list, got {type(quest['memos'])}"
    prompt = f"""Analyze the following journal entry and extract tasks, updates and important memos related to the user's quests. If a new task, update or memo would better be suited for a new quest, create one accordingly.
    
    Return the results as a JSON object with two main keys: "info" and "quest_descriptions".
    
    The "info" should be an array of objects, each containing:
    1. "quest_title": Title of the quest (create a new one if it doesn't match existing quests)
    2. "type": Either 'task', 'update' or 'memo'
    3. "content": Content of the task or update
    4. "scheduled_date_time": Date/time for tasks (null if not applicable)

    The "quest_descriptions" should be an object where each key is a quest title, and the value is the updated description for that quest.
    
    Some entries may have multiple tasks or updates related to different or the same quests. Atomize tasks as much as possible.
    
    Writing Style:
        Take inspiration from the user's journal entries to make the quest descriptions engaging, detailed and immersive, like in RPGs such as Elder Scrolls.
        Create your writing in a fashion inspired by Disco Elysium, Ernest Hemingway and Ulysses from Fallout: New Vegas. Don't be afraid to be extensive: give me a long description based on the information provided. Descriptions should explain the goals, aims, backgrounds and upcoming tasks of the quest.
    
    Existing Quests: {json.dumps(quest_data)}
    
    Journal Entry: {entry.content}

    Please format your response exactly as follows:

    {{
        "info": [
            {{
                "quest_title": "String: Title of the quest",
                "type": "String: Either 'task', 'update' or 'memo'",
                "content": "String: Content of the task or update or important memos to remember about the quest",
                "scheduled_date_time": "String: Date/time for tasks (null if not applicable)"
            }},
            ...
        ],
        "quest_descriptions": [ 
        {{
            "Quest Title 1": "String: Updated description for Quest 1",
            "Quest Title 2": "String: Updated description for Quest 2",
            }}
            ...
        ]
    }}

    
    Only output updated descriptions for quests that have been affected by a task, update or memo.
    Ensure that the output is a valid JSON object and that all fields are present for each item, using null for any fields that are not applicable.

    """
    
    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[
                {"role": "system", "content": "You are a storyteller that analyzes journal entries to extract tasks, updates, and description changes related to ongoing quests. You always return your response as a valid JSON object."},
                {"role": "user", "content": prompt}
            ],
        )
        
        raw_content = response.choices[0].message.content
        print("Raw API Response:", raw_content)
        
        # Clean up the response by removing triple backticks and any "json" label
        if raw_content.startswith("```json"):
            raw_content = raw_content.lstrip("```json").rstrip("```").strip()
        elif raw_content.startswith("```"):
            raw_content = raw_content.lstrip("```").rstrip("```").strip()

        # Attempt to parse the JSON response
        try:
            results = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError as json_err:
            print(f"JSON Decode Error for entry {entry.id}: {str(json_err)}")
            print("Raw LLM Response:", response.choices[0].message.content)
            return  # Exit the function if JSON parsing fails
        
        info = results['info']
        if not isinstance(info, list):
            print(f"Incompatibleaaaaaa collection type: {type(info)} is not list-like")
            return
        
        # Process tasks and updates
        for item in info:
            quest_title = item.get('quest_title')
            if not quest_title:
                print(f"Missing quest_title in item for entry {entry.id}")
                continue

            quest = next((q for q in quests if q.title.lower() == quest_title.lower()), None)
            if not quest: # Create a new quest if it doesn't exist
                quest = Quest(title=quest_title, description='')
                if not quest.id:
                 print(f"Error: quest ID not assigned for quest '{quest_title}'")
                else:
                    print(f"Quest '{quest_title}' successfully generated with ID {quest.id}.")
                db.session.add(quest)

                if not quest.id:
                    print(f"Error: quest ID not assigned for quest '{quest_title}'")
                    db.session.rollback()
                    return
                quests.append(quest)  # Add the new quest to our list
            
            try:
                db.session.commit()
                print(f"Quest '{quest.title}' successfully added with ID {quest.id}.")
            except SQLAlchemyError as e:
                db.session.rollback()
                print(f"Database error while processing quest '{quest.title}': {str(e)}")
                return
            
            item_type = item.get('type')
            if item_type == 'task':
                content = item.get('content')
                if not content:
                    print(f"Missing content for task in entry {entry.id}")
                    continue

                scheduled_date = None
                if item.get('scheduled_date_time'):
                        scheduled_date = parse_date(item['scheduled_date_time'])
                else:
                        print(f"Invalid date format for entry {entry.id}: {str(item['scheduled_date_time'])}")

                quest.add_task(content, scheduled_date)
            elif item_type == 'update':
                # For updates, we'll update the quest description later
                pass
            elif item_type == 'memo':
                content = item.get('content')
                if not content:
                    print(f"Missing content for memo in entry {entry.id}")
                    continue
                quest.add_memo(content)

        # Update quest descriptions
        print("update quests")
        for quest_title, new_description in results['quest_descriptions'].items():
            quest = next((q for q in quests if q.title.lower() == quest_title.lower()), None)
            if quest:
                quest.update_description(quest.id, new_description)
            else:
                print(f"Quest '{quest_title}' not found for updating description")

        db.session.commit()
        print(f"Successfully analyzed journal entry {entry.id}")
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Database error while processing entry {entry.id}: {str(e)}")
