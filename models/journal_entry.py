# models/journal_entry.py
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

from models.db import db

class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)