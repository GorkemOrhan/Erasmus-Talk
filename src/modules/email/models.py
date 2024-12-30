from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from src.core.database import Base

class MailTemplate(Base):
    __tablename__ = 'mail_templates'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    subject = Column(String(255), nullable=False)
    html_body = Column(Text, nullable=False)
    text_body = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pending_mails = relationship('PendingMail', back_populates='template')

class PendingMail(Base):
    __tablename__ = 'pending_mails'

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey('mail_templates.id'))
    recipient_email = Column(String(255), nullable=False)
    recipient_name = Column(String(255))
    template_data = Column(JSON)
    status = Column(String(50), default='pending')
    retry_count = Column(Integer, default=0)
    next_retry_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    idempotency_key = Column(String(255), unique=True)

    # Relationships
    template = relationship('MailTemplate', back_populates='pending_mails')
    logs = relationship('MailLog', back_populates='pending_mail')

class MailLog(Base):
    __tablename__ = 'mail_logs'

    id = Column(Integer, primary_key=True)
    pending_mail_id = Column(Integer, ForeignKey('pending_mails.id'))
    status = Column(String(50), nullable=False)
    error_message = Column(Text)
    provider_response = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    pending_mail = relationship('PendingMail', back_populates='logs') 