
from datetime import datetime
from models.db import db
from flask_sqlalchemy import SQLAlchemy

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('ChatMessage', backref='conversation', lazy=True, cascade="all, delete-orphan")