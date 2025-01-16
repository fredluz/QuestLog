from openai import OpenAI
import json
from sqlalchemy.exc import SQLAlchemyError
from models.db import db
from models.conversation import Conversation
from models.chat import ChatMessage
from models.quest import Quest
from models.journal_entry import JournalEntry
from flask import request, jsonify
from datetime import datetime

def get_all_quest_and_journal_data():
    quests = Quest.query.all()
    journal_entries = JournalEntry.query.all()
    
    quest_data = [{
        "title": quest.title, 
        "description": [desc.content for desc in quest.description],
        "tasks": [task.content for task in quest.tasks],
        "memos": [memo.content for memo in quest.memos]
    } for quest in quests]
    
    journal_data = [{"content": entry.content} for entry in journal_entries]
    
    return quest_data, journal_data

def start_new_conversation():
    new_conv = Conversation()
    db.session.add(new_conv)
    db.session.commit()
    return new_conv.id

def get_conversations():
    conversations = Conversation.query.order_by(Conversation.created_at.desc()).all()
    conv_list = [{
        "id": conv.id,
        "title": conv.title if conv.title else f"Conversation {conv.id}",
        "created_at": conv.created_at.isoformat()
    } for conv in conversations]
    return conv_list

def get_conversation_messages(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    messages = ChatMessage.query.filter_by(conversation_id=conversation_id).order_by(ChatMessage.date.asc()).all()
    chat_log = [{
        "role": msg.role,
        "message": msg.message,
        "date": msg.date.isoformat()
    } for msg in messages]
    return chat_log

def send_message():
    data = request.get_json()
    conversation_id = data.get("conversation_id")
    user_msg = data.get("message")
    
    if not conversation_id:
        return jsonify({"error": "No conversation ID provided"}), 400
    if user_msg is None:
        return jsonify({"error": "No message provided"}), 400
    
    conversation = Conversation.query.get_or_404(conversation_id)
    
    # Store user message
    user_entry = ChatMessage(message=user_msg, role="user", conversation=conversation)
    db.session.add(user_entry)
    db.session.commit()
    
    # Build conversation context
    quest_data, journal_data = get_all_quest_and_journal_data()
    system_message = f"""You are an AI assistant with knowledge of all quests and journal entries in a user's RPG-like life management system. 
Use this information to answer questions and provide insights, as if a personal mentor or guide in an RPG. Make sure to provide detailed, engaging, and immersive responses.

Quests: {json.dumps(quest_data)}
Journal Entries: {json.dumps(journal_data)}

Respond in a style inspired by Disco Elysium and Ulysses from Fallout: New Vegas.
Be engaging, detailed, and immersive in your responses."""
    
    # Retrieve all messages in the conversation
    all_msgs = ChatMessage.query.filter_by(conversation_id=conversation_id).order_by(ChatMessage.date.asc()).all()
    messages = [{"role": "system", "content": system_message}]
    for msg in all_msgs:
        messages.append({"role": msg.role, "content": msg.message})
    
    # Call OpenAI
    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use the latest available model
            messages=messages
        )
        ai_text = response.choices[0].message.content
        # Store AI response
        ai_entry = ChatMessage(message=ai_text, role="assistant", conversation=conversation)
        db.session.add(ai_entry)
        db.session.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    # Return updated messages
    chat_log = get_conversation_messages(conversation_id)
    return jsonify({"chat_log": chat_log})

def api_chat():
    action = request.args.get("action")
    if action == "start":
        conv_id = start_new_conversation()
        return jsonify({"conversation_id": conv_id})
    elif action == "list":
        conv_list = get_conversations()
        return jsonify({"conversations": conv_list})
    elif action == "send":
        return send_message()
    elif action == "get":
        conversation_id = request.args.get("conversation_id")
        if not conversation_id:
            return jsonify({"error": "No conversation ID provided"}), 400
        chat_log = get_conversation_messages(conversation_id)
        return jsonify({"chat_log": chat_log})
    else:
        return jsonify({"error": "Invalid action"}), 400