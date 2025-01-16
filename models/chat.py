from datetime import datetime
from models.db import db
from flask_sqlalchemy import SQLAlchemy

class ChatMessage(db.Model):
    __tablename__ = 'ChatMessage'  # Add this line to specify exact table name
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.String(20), default="user")  # "user" or "assistant"
