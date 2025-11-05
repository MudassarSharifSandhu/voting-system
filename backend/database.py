from sqlalchemy import (
    create_engine, Column, String, Integer, DateTime, Boolean
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class VoteSession(Base):
    """Tracks device sessions and their vote counts"""
    __tablename__ = "vote_sessions"

    id = Column(Integer, primary_key=True, index=True)
    fingerprint = Column(String, unique=True, index=True, nullable=False)
    token = Column(String, nullable=False)
    token_expires_at = Column(DateTime, nullable=False)
    votes_used = Column(Integer, default=0, nullable=False)
    ip_address = Column(String, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_suspicious = Column(Boolean, default=False)


class Vote(Base):
    """Records individual votes"""
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True)
    fingerprint = Column(String, index=True, nullable=False)
    contestant = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_via_captcha = Column(Boolean, default=False)
    verified_via_sms = Column(Boolean, default=False)


class RateLimitLog(Base):
    """Tracks rate limit violations"""
    __tablename__ = "rate_limit_logs"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, index=True, nullable=False)
    fingerprint = Column(String, index=True, nullable=False)
    endpoint = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class IPChangeLog(Base):
    """Tracks IP address changes per fingerprint (VPN/proxy detection)"""
    __tablename__ = "ip_change_logs"

    id = Column(Integer, primary_key=True, index=True)
    fingerprint = Column(String, index=True, nullable=False)
    old_ip = Column(String, nullable=True)
    new_ip = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
