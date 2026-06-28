from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class Scheme(Base):
    """Government scheme data stored in SQLite."""
    __tablename__ = "schemes"

    id = Column(String, primary_key=True)  # URL slug or UUID
    name = Column(String, nullable=False)
    eligibility = Column(Text, nullable=False)
    benefits = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    application_process = Column(Text, nullable=True)
    required_documents = Column(JSON, nullable=True)
    ministry = Column(String, nullable=True)
    application_url = Column(String, nullable=True)
    category = Column(String, nullable=False)
    state = Column(String, nullable=True)  # NULL = national scheme
    status = Column(String, default="active")  # active, inactive
    tags = Column(JSON, nullable=True)  # List of tags
    source_url = Column(String, nullable=False)
    last_synced_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserProfile(Base):
    """User profile data (Clerk user_id as primary key)."""
    __tablename__ = "user_profiles"

    user_id = Column(String, primary_key=True)  # Clerk user ID
    name = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    state = Column(String, nullable=True)
    area = Column(String, nullable=True)  # rural/urban
    caste_category = Column(String, nullable=True)  # SENSITIVE - never returned in API
    annual_income = Column(Integer, nullable=True)  # SENSITIVE - never returned in API
    has_disability = Column(Boolean, nullable=True)  # SENSITIVE - never returned in API
    occupation = Column(String, nullable=True)
    is_student = Column(Boolean, nullable=True)
    education_level = Column(String, nullable=True)
    marital_status = Column(String, nullable=True)
    has_children = Column(Boolean, nullable=True)
    is_pregnant = Column(Boolean, nullable=True)
    bpl_card = Column(Boolean, nullable=True)  # SENSITIVE
    goals = Column(JSON, nullable=True)  # List of user goals
    profile_strength = Column(Integer, default=0)  # 0-100 completeness score
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversation(Base):
    """Conversation session for multi-turn chat."""
    __tablename__ = "conversations"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user_profiles.user_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to messages
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Individual messages in a conversation."""
    __tablename__ = "messages"

    id = Column(String, primary_key=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to conversation
    conversation = relationship("Conversation", back_populates="messages")


class Notification(Base):
    """User notifications for scheme eligibility."""
    __tablename__ = "notifications"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user_profiles.user_id"), nullable=False)
    scheme_id = Column(String, ForeignKey("schemes.id"), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, nullable=False)  # new_scheme, expiring_scheme, eligibility_match
    is_read = Column(Boolean, default=False)
    is_cancelled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
