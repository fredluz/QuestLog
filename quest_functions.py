from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from datetime import datetime
import os
import json
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from models.db import db
from models.quest import Quest
from models.task import Task
from models.memo import Memo
from models.quest_description import QuestDescription

def Q_quests():
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

def Q_rename_quest(quest_id, new_title):
    quest = Quest.query.get_or_404(quest_id)
    quest.title = new_title
    db.session.commit()
    flash("Quest renamed successfully", "success")
    return redirect(url_for('quest_details', quest_id=quest_id))

def Q_delete_quest(quest_id):
    quest = Quest.query.get_or_404(quest_id)
    try:
        db.session.delete(quest)
        db.session.commit()
        flash("Quest deleted successfully", "success")
    except IntegrityError as e:
        db.session.rollback()
        flash("An error occurred while deleting the quest. Please try again.", "error")
    except Exception as e:
        db.session.rollback()
        flash("An unexpected error occurred. Please try again.", "error")
    return redirect(url_for('quests'))


def Q_delete_memo(memo_id):
    memo = Memo.query.get_or_404(memo_id)
    quest_id = memo.quest_id
    db.session.delete(memo)
    db.session.commit()
    flash("Memo deleted successfully", "success")
    return redirect(url_for('quest_details', quest_id=quest_id))

def Q_edit_quest_description(quest_id, new_description):
    quest = Quest.query.get_or_404(quest_id)
    
    new_description_entry = QuestDescription(
        quest_id=quest.id,
        content=quest.description.content,
        timestamp=datetime.utcnow()
    )
    db.session.add(new_description_entry)
    
    quest.description = new_description
    db.session.commit()
    
    return jsonify({"message": "Quest description updated successfully"}), 200


def Q_quest_details(quest_id):
    quest = Quest.query.get_or_404(quest_id)
    tasks = Task.query.filter_by(quest_id=quest_id).all()
    memos = quest.get_memos()
    descriptions = QuestDescription.query.filter_by(quest_id=quest_id).order_by(QuestDescription.timestamp.desc()).all()
    
    return render_template('quest_details.html', quest=quest, tasks=tasks, memos=memos, descriptions=descriptions)