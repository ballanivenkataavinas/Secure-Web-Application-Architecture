from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from .database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    is_admin = Column(Boolean, default=False)
    failed_attempts = Column(Integer, default=0)
    lockout_until = Column(DateTime, nullable=True)
    warning_count = Column(Integer, default=0)
    ban_until = Column(DateTime, nullable=True)

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, nullable=False, unique=True)
    user_id = Column(String, ForeignKey("users.username"))
    expires_at = Column(DateTime)
    revoked = Column(Boolean, default=False)
    

class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String)
    text = Column(String)
    severity = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class Offense(Base):
    __tablename__ = "offenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    count = Column(Integer, default=0)
    last_offense = Column(DateTime(timezone=True), server_default=func.now())
    severity_score = Column(Integer, default=0)
    lockout_until = Column(DateTime(timezone=True), nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    user = Column(String, nullable=True)  # username
    action = Column(String, nullable=False)
    endpoint = Column(String, nullable=False)

    ip_address = Column(String, nullable=False)  # ✅ IP stored here
    user_agent = Column(String, nullable=True)   # optional but powerful

    timestamp = Column(DateTime, default=datetime.utcnow)