import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
from config import paths

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    chats = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("CoreMemory", back_populates="user", cascade="all, delete-orphan")

class ChatHistory(Base):
    __tablename__ = 'chat_history'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    message_json = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    active = Column(Integer, default=1)
    
    user = relationship("User", back_populates="chats")

# Index for fast querying of recent messages
Index('idx_chat_user_time', ChatHistory.user_id, ChatHistory.timestamp.desc())

class CoreMemory(Base):
    __tablename__ = 'core_memories'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    fact = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="memories")

class ChatSummary(Base):
    __tablename__ = 'chat_summaries'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    summary_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")

class PendingCommand(Base):
    __tablename__ = 'pending_commands'
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    command = Column(Text, nullable=False)
    telegram_id = Column(String(50), nullable=False)
    status = Column(String(20), default="pending") # pending, completed, denied
    created_at = Column(DateTime, default=datetime.utcnow)

# Database Setup
def get_db_url():
    data_dir = paths.get_data_dir()
    db_path = os.path.join(data_dir, "jarvish.db")
    return f"sqlite:///{db_path}"

engine = create_engine(get_db_url(), connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_session():
    return SessionLocal()
