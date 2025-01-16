from openai import OpenAI
import json
from sqlalchemy.exc import SQLAlchemyError
from models.db import db
from models.quest import Quest
from models.journal_entry import JournalEntry

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

def chat_with_quest_llm():
    client = OpenAI()
    quest_data, journal_data = get_all_quest_and_journal_data()
    
    system_message = f"""You are an AI assistant with knowledge of all quests and journal entries in a user's RPG-like life management system. 
    Use this information to answer questions and provide insights, as if a personal mentor or guide in an RPG. Make sure to provide detailed, engaging, and immersive responses.
    
    Quests: {json.dumps(quest_data)}
    Journal Entries: {json.dumps(journal_data)}
    
    Respond in a style inspired by Disco Elysium and Ulysses from Fallout: New Vegas.
    Be engaging, detailed, and immersive in your responses."""
    
    messages = [
        {"role": "system", "content": system_message}
    ]
    
    print("Welcome to the Quest Chat Interface!")
    print("You can chat with an AI that knows about all your quests and journal entries.")
    print("Type 'exit' to end the conversation.")
    
    while True:
        user_input = input("\nYou: ")
        
        if user_input.lower() == 'exit':
            print("Goodbye!")
            break
        
        messages.append({"role": "user", "content": user_input})
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Use the latest available model
                messages=messages
            )
            
            ai_response = response.choices[0].message.content
            print("\nAI:", ai_response)
            
            messages.append({"role": "assistant", "content": ai_response})
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            break

if __name__ == "__main__":
    chat_with_quest_llm()