# models/quest.py
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

from models.db import db

from .task import Task
from .memo import Memo
from .quest_description import QuestDescription

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
