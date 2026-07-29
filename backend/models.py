from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from database import Base

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_order=True, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    spawn_command = Column(String(500), nullable=True)
    crafting_recipe = Column(JSON, nullable=True)  # ex: {"Wood": 10, "Stone": 5}
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relație 1-la-1 cu tabelul de vectori
    embedding = relationship("ItemEmbedding", back_populates="item", uselist=False, cascade="all, delete-orphan")


class ItemEmbedding(Base):
    __tablename__ = "item_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), unique=True, nullable=False)
    # Vector de dimensiune 1536 (standard OpenAI text-embedding-3-small)
    vector = Column(Vector(1536), nullable=False)

    item = relationship("Item", back_populates="embedding")