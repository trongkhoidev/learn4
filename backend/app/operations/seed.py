from app.db.session import SessionLocal
from app.modules.speaking.models import SpeakingQuestion, SpeakingTopic

def seed_speaking_data():
    db = SessionLocal()
    try:
        if db.query(SpeakingTopic).count() == 0:
            topics_data = [
                {
                    "name": "Hometown",
                    "description": "Questions about where you grew up",
                    "questions": [
                        {"part": 1, "text": "Where is your hometown?"},
                        {"part": 1, "text": "Do you like your hometown?"},
                        {"part": 2, "text": "Describe a place you like in your hometown. You should say: where it is, what it looks like, what you do there, and explain why you like it."},
                        {"part": 3, "text": "How has your hometown changed in recent years?"},
                        {"part": 3, "text": "What are the advantages of living in a small town compared to a big city?"}
                    ]
                },
                {
                    "name": "Hobbies",
                    "description": "Questions about your free time activities",
                    "questions": [
                        {"part": 1, "text": "What do you do in your free time?"},
                        {"part": 2, "text": "Describe a hobby you enjoy. You should say: what it is, when you do it, who you do it with, and explain why you enjoy it."},
                        {"part": 3, "text": "Why is it important for people to have hobbies?"}
                    ]
                }
            ]
            
            for t_data in topics_data:
                topic = SpeakingTopic(name=t_data["name"], description=t_data["description"])
                db.add(topic)
                db.commit()
                db.refresh(topic)
                
                for q_data in t_data["questions"]:
                    question = SpeakingQuestion(
                        topic_id=topic.id,
                        part=q_data["part"],
                        question_text=q_data["text"]
                    )
                    db.add(question)
            
            db.commit()
    finally:
        db.close()
