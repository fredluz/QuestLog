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
from journal_analysis import analyze_entry

def J_delete_journal_entry(entry_id):
    entry = JournalEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash("Journal entry deleted successfully", "success")
    return redirect(url_for('journal'))

def J_journal():
    if request.method == 'POST':
        content = request.form['content']
        if not content:
            flash("No content provided", "error")
            return redirect(url_for('journal'))
        
        new_entry = JournalEntry(content=content)
        db.session.add(new_entry)
        db.session.commit()
        
        print(f"Journal entry added: {new_entry.content}")
        
        analyze_entry(new_entry)
        
        flash("Journal entry added and analyzed successfully", "success")
        return redirect(url_for('journal'))
    
    entries = JournalEntry.query.order_by(JournalEntry.date.desc()).all()
    return render_template('journal.html', entries=entries)