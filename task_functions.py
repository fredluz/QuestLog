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
from models.journal_entry import JournalEntry


def T_tasks():
    # Fetch all tasks from all quests
    all_tasks = Task.query.order_by(Task.scheduled_date).all()
    
    # Group tasks by quest
    tasks_by_quest = {}
    for task in all_tasks:
        if task.quest.title not in tasks_by_quest:
            tasks_by_quest[task.quest.title] = []
        tasks_by_quest[task.quest.title].append(task)
    
    return render_template('tasks.html', tasks_by_quest=tasks_by_quest)



def T_add_task(quest_id):
    from app import parse_date
    quest = Quest.query.get_or_404(quest_id)
    content = request.form['content']
    scheduled_date = request.form.get('scheduled_date')
    if scheduled_date == "mm/dd/yyyy":
        scheduled_date = '9999-12-12'
    if scheduled_date:
        # Use the parse_date function to convert the date string to a datetime object
        scheduled_date = parse_date(scheduled_date)
        if scheduled_date is None:
            return redirect(url_for('quest_details', quest_id=quest_id))
        
    quest.add_task(content, scheduled_date)
    db.session.commit()
    flash("Task added successfully", "success")
    return redirect(url_for('quest_details', quest_id=quest_id))

def T_delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    quest_id = task.quest_id
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted successfully", "success")
    return redirect(url_for('quest_details', quest_id=quest_id))