# models/quest_description.py
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

from models.db import db

class QuestDescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quest_id = db.Column(db.Integer, db.ForeignKey('quest.id', ondelete='CASCADE', name='fk_quest_description_quest'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)