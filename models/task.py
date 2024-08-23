# models/task.py
from flask_sqlalchemy import SQLAlchemy

from models.db import db

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    scheduled_date = db.Column(db.DateTime, nullable=True)
    completed = db.Column(db.Boolean, default=False)
    quest_id = db.Column(db.Integer, db.ForeignKey('quest.id', ondelete='CASCADE', name='fk_task_quest'), nullable=False)