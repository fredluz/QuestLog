from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from openai import OpenAI
import os
import json
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from flask_migrate import Migrate


load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quest_log.db'
app.secret_key = os.getenv("SECRET_KEY")  # Replace with a real secret key
db = SQLAlchemy(app)
migrate = Migrate(app, db)

openai_api_key = os.getenv("OPENAI_API_KEY")
OpenAI.api_key = openai_api_key

# Database Models
class Quest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    tasks = db.relationship('Task', backref='quest', lazy=True, cascade="all, delete-orphan")
    memos = db.relationship('Memo', backref='quest', lazy=True, cascade="all, delete-orphan")
    description = db.relationship('QuestDescription', backref='quest', lazy=True, cascade="all, delete-orphan", order_by="QuestDescription.timestamp.desc()")

    def __init__(self, title, description):
        self.title = title
        db.session.add(self)
        db.session.flush()
        db.session.commit()

        # Save the initial description
        self.save_initial_description(description)

    def save_initial_description(self, description):
        if description:  # Check if the description is not empty
            initial_description_entry = QuestDescription(
                quest_id=self.id,
                content=description,  # Save the description text in the 'content' column
                timestamp=datetime.utcnow()
            )
            db.session.add(initial_description_entry)
            db.session.commit()

    def update_description(self, questtempid, new_description):
        # Save the current description with its timestamp before updating
        if self.description:
            old_description_entry = QuestDescription(
                quest_id=questtempid,
                content=self.description[-1].content if self.description else '',  # Get the last description if it exists
                timestamp=self.get_current_description_timestamp()
            )
            db.session.add(old_description_entry)

        # Add the new description as a new QuestDescription object
        new_description_entry = QuestDescription(
            quest_id=self.id,
            content=new_description,  # Save the new description text in the 'content' column
            timestamp=datetime.utcnow()
        )
        db.session.add(new_description_entry)
        db.session.commit()

        # Ensure the relationship is updated (not strictly necessary but keeps the session synced)
        self.description.append(new_description_entry)

    def get_current_description(self):
        """Retrieve the most recent description."""
        if self.description:
            return self.description[0].content  # Get the most recent description
        return None

    def get_current_description_timestamp(self):
        # Retrieve the timestamp of the most recent description from the database
        latest_description = QuestDescription.query.filter_by(
            quest_id=self.id
        ).order_by(QuestDescription.timestamp.desc()).first()
        
        if latest_description:
            return latest_description.timestamp
        else:
            return datetime.utcnow()  # Fallback, though this case shouldn't occur
    def add_task(self, content, scheduled_date=None):
        new_task = Task(content=content, scheduled_date=scheduled_date, quest_id=self.id)
        db.session.add(new_task)

    def get_tasks(self):
        return self.tasks
        

    def add_memo(self, content):
        new_memo = Memo(content=content, quest_id=self.id)
        db.session.add(new_memo)

    def get_memos(self):
        return self.memos


class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    
class QuestDescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quest_id = db.Column(db.Integer, db.ForeignKey('quest.id', ondelete='CASCADE', name='fk_quest_description_quest'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    scheduled_date = db.Column(db.DateTime, nullable=True)
    completed = db.Column(db.Boolean, default=False)
    quest_id = db.Column(db.Integer, db.ForeignKey('quest.id', ondelete='CASCADE', name='fk_task_quest'), nullable=False)

class Memo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    quest_id = db.Column(db.Integer, db.ForeignKey('quest.id', ondelete='CASCADE', name='fk_memo_quest'), nullable=False)

# Routes

from flask import current_app
from sqlalchemy import text


@app.route('/')
def home():
    print(os.getenv("OPENAI_API_KEY"))
    return render_template('home.html')

@app.route('/journal', methods=['GET', 'POST'])
def journal():
    if request.method == 'POST':
        content = request.form['content']
        if not content:
            flash("No content provided", "error")
            return redirect(url_for('journal'))
        
        new_entry = JournalEntry(content=content)
        db.session.add(new_entry)
        db.session.commit()
        
        print(f"Journal entry added: {new_entry.content}")
        
        analyze_journal_entry(new_entry)
        
        flash("Journal entry added and analyzed successfully", "success")
        return redirect(url_for('journal'))
    
    entries = JournalEntry.query.order_by(JournalEntry.date.desc()).all()
    return render_template('journal.html', entries=entries)

@app.route('/quests', methods=['GET', 'POST'])
def quests():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        new_quest = Quest(title=title, description="a")
        db.session.add(new_quest)
        db.session.commit()
        new_quest.update_description(new_quest.id, description)
        flash("Quest added successfully", "success")
        return redirect(url_for('quests'))
    quests = Quest.query.all()
    return render_template('quests.html', quests=quests)

@app.route('/quest/<int:quest_id>/task', methods=['POST'])
def add_task(quest_id):
    quest = Quest.query.get_or_404(quest_id)
    content = request.form['content']
    scheduled_date = request.form.get('scheduled_date')
    if scheduled_date:
        scheduled_date = datetime.strptime(scheduled_date, '%Y-%m-%d').strftime('%d/%m/%y')
    quest.add_task(content, scheduled_date)
    db.session.commit()
    flash("Task added successfully", "success")
    return redirect(url_for('quest_details', quest_id=quest_id))

@app.route('/quest/<int:quest_id>/rename', methods=['POST'])
def rename_quest(quest_id):
    quest = Quest.query.get_or_404(quest_id)
    new_title = request.form['new_title']
    
    # Update the quest title
    quest.title = new_title
    db.session.commit()
    
    flash("Quest renamed successfully", "success")
    return redirect(url_for('quest_details', quest_id=quest_id))

@app.route('/tasks')
def tasks():
    # Fetch all tasks from all quests
    all_tasks = Task.query.order_by(Task.scheduled_date).all()
    
    # Group tasks by quest
    tasks_by_quest = {}
    for task in all_tasks:
        if task.quest.title not in tasks_by_quest:
            tasks_by_quest[task.quest.title] = []
        tasks_by_quest[task.quest.title].append(task)
    
    return render_template('tasks.html', tasks_by_quest=tasks_by_quest)

@app.route('/quest/<int:quest_id>/delete', methods=['POST'])
def delete_quest(quest_id):
    quest = Quest.query.get_or_404(quest_id)
    try:
        db.session.delete(quest)
        db.session.commit()
        flash("Quest deleted successfully", "success")
    except IntegrityError as e:
        db.session.rollback()
        flash("An error occurred while deleting the quest. Please try again.", "error")
        app.logger.error(f"Error deleting quest: {str(e)}")
    except Exception as e:
        db.session.rollback()
        flash("An unexpected error occurred. Please try again.", "error")
        app.logger.error(f"Unexpected error deleting quest: {str(e)}")
    return redirect(url_for('quests'))

@app.route('/task/<int:task_id>/delete', methods=['POST'])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    quest_id = task.quest_id
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted successfully", "success")
    return redirect(url_for('quest_details', quest_id=quest_id))

@app.route('/memo/<int:memo_id>/delete', methods=['POST'])
def delete_memo(memo_id):
    memo = Memo.query.get_or_404(memo_id)
    quest_id = memo.quest_id
    db.session.delete(memo)
    db.session.commit()
    flash("Memo deleted successfully", "success")
    return redirect(url_for('quest_details', quest_id=quest_id))

@app.route('/delete_journal_entry/<int:entry_id>', methods=['POST'])
def delete_journal_entry(entry_id):
    entry = JournalEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash("Journal entry deleted successfully", "success")
    return redirect(url_for('journal'))
# LLM Integration

def to_dict(model):
    """Convert a SQLAlchemy model object to a dictionary."""
    return {column.name: getattr(model, column.name) for column in model.__table__.columns}

def analyze_journal_entry(entry):
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


@app.route('/quest/<int:quest_id>/edit_description', methods=['POST'])
def edit_quest_description(quest_id):
    quest = Quest.query.get_or_404(quest_id)
    
    # Save the current description as a new entry in QuestDescription
    new_description_entry = QuestDescription(
        quest_id=quest.id,
        content=quest.description.content,
        timestamp=datetime.utcnow()
    )
    db.session.add(new_description_entry)
    
    # Update the quest's current description
    new_description = request.form['description']
    quest.description = new_description
    db.session.commit()
    
    return jsonify({"message": "Quest description updated successfully"}), 200

@app.route('/quest/<int:quest_id>')
def quest_details(quest_id):
    quest = Quest.query.get_or_404(quest_id)
    tasks = Task.query.filter_by(quest_id=quest_id).all()
    memos = quest.get_memos()
    descriptions = QuestDescription.query.filter_by(quest_id=quest_id).order_by(QuestDescription.timestamp.desc()).all()
    
    return render_template('quest_details.html', quest=quest, tasks=tasks, memos=memos, descriptions=descriptions)


@app.route('/status')
def status():
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

def parse_date(date_string):
    date_formats = [
        "%Y-%m-%d",
        "%d/%m/%y",
        "%d/%m/%Y",
        "%B %d",
        "%b %d",
        "%d %B",
        "%d %b"
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            pass
    
    

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)