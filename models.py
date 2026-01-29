from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone # <--- 1. Import timezone
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    # --- NEW: Gamification ---
    xp = db.Column(db.Integer, default=0) 

    def set_password(self, password):
        self.password_hash = password
        
    def check_password(self, password):
        return self.password_hash == password
        
    # Helper to calculate level based on XP (e.g., Level up every 500 XP)
    def get_level(self):
        return int(self.xp / 500) + 1

class TopicAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic_name = db.Column(db.String(200), nullable=False)
    
    # 2. FIX: Use a lambda to call .now(timezone.utc)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    roadmap_json = db.Column(db.Text, nullable=True) 
    current_node_index = db.Column(db.Integer, default=0)
    is_deep_dive = db.Column(db.Boolean, default=False)

    def get_roadmap(self):
        if self.roadmap_json:
            return json.loads(self.roadmap_json)
        return None

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_attempt_id = db.Column(db.Integer, db.ForeignKey('topic_attempt.id'), nullable=False)
    
    node_index = db.Column(db.Integer, nullable=False)
    node_title = db.Column(db.String(200))
    
    content_markdown = db.Column(db.Text)
    quiz_json = db.Column(db.Text)

class NodeResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_attempt_id = db.Column(db.Integer, db.ForeignKey('topic_attempt.id'))
    node_index = db.Column(db.Integer)
    node_title = db.Column(db.String(200))
    score = db.Column(db.Integer)
    passed = db.Column(db.Boolean, default=False)
    
    # 2. FIX: Same here
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))