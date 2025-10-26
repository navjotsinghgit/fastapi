from db import Base

from sqlalchemy import Column, Integer, String, DateTime, func

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=True)
    role = Column(String, nullable=True)
    theme_preference = Column(String, nullable=True, server_default="dark")  # dark or light
    created_at = Column(DateTime(timezone=True), server_default=func.now())