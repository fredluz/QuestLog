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

from models.db import db

from status import generate_status
from journal_analysis import analyze_entry


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quest_log.db'

app.secret_key = os.getenv("SECRET_KEY")  # Replace with a real secret key
db.init_app(app)

with app.app_context():
    db.create_all()
migrate = Migrate(app, db)

from models.quest import Quest
from models.task import Task
from models.memo import Memo
from models.quest_description import QuestDescription
from models.journal_entry import JournalEntry

from quest_functions import (
    Q_quests,
    Q_rename_quest,
    Q_delete_quest,
    Q_delete_memo,
    Q_edit_quest_description,
    Q_quest_details
)

from journal_functions import (
    J_delete_journal_entry,
    J_journal
)

from task_functions import (
    T_tasks,
    T_add_task,
    T_delete_task

)

openai_api_key = os.getenv("OPENAI_API_KEY")
OpenAI.api_key = openai_api_key

@app.route('/')
def home():
    print(os.getenv("OPENAI_API_KEY"))
    return render_template('home.html')

@app.route('/journal', methods=['GET', 'POST'])
def journal():
    return J_journal()
        

@app.route('/quests', methods=['GET', 'POST'])
def quests():
    return Q_quests() 

@app.route('/quest/<int:quest_id>/task', methods=['POST'])
def add_task(quest_id):
   return T_add_task(quest_id)

@app.route('/quest/<int:quest_id>/rename', methods=['POST'])
def rename_quest(quest_id):
    return Q_rename_quest(quest_id)

@app.route('/tasks')
def tasks():
    
    return T_tasks()

@app.route('/quest/<int:quest_id>/delete', methods=['POST'])
def delete_quest(quest_id):
    return Q_delete_quest(quest_id)

@app.route('/task/<int:task_id>/delete', methods=['POST'])
def delete_task(task_id):
    return T_delete_task(task_id)

@app.route('/memo/<int:memo_id>/delete', methods=['POST'])
def delete_memo(memo_id):
    return Q_delete_memo(memo_id)

@app.route('/delete_journal_entry/<int:entry_id>', methods=['POST'])
def delete_journal_entry(entry_id):
    return J_delete_journal_entry(entry_id)

# LLM Integration

#def to_dict(model):
#    """Convert a SQLAlchemy model object to a dictionary."""
#    return {column.name: getattr(model, column.name) for column in model.__table__.columns}
#   no idea if this is even used but im scared to delete it

def analyze_journal_entry(entry):
    return analyze_entry(entry)
    

@app.route('/quest/<int:quest_id>/edit_description', methods=['POST'])
def edit_quest_description(quest_id):
    return Q_edit_quest_description(quest_id)

@app.route('/quest/<int:quest_id>')
def quest_details(quest_id):
    return Q_quest_details(quest_id)

@app.route('/status')
def status():
    return generate_status()


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