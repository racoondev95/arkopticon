from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# Asigură-te că `Base` provine din fișierul tău de configurare a DB (ex: database.py)
from database import Base


class WikiItemModel(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, index=True)
    wiki_url = Column(String, nullable=True)
    description = Column(String, nullable=True)
    spawn_command = Column(String, nullable=True)
    spawn_command_short = Column(String, nullable=True)
    spawn_command_long = Column(String, nullable=True)
    gfi = Column(String, nullable=True)
    blueprint = Column(String, nullable=True)

    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())