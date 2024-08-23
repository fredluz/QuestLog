# models/memo.py
from flask_sqlalchemy import SQLAlchemy

from models.db import db

class Memo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    quest_id = db.Column(db.Integer, db.ForeignKey('quest.id', ondelete='CASCADE', name='fk_memo_quest'), nullable=False)