from typing import Optional
from fastapi import Depends, FastAPI, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from database import engine, Base
import models
from database import get_db
from models import WikiItemModel
from api.services.wiki_client import ArkWikiClient, sync_and_get_category
from .database import get_db
app = FastAPI(title="Arkopticon API")
wiki_client = ArkWikiClient()

@app.on_event("startup")
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/api/wiki/{category_name}")
async def get_category_data(
    category_name: str,
    limit: Optional[int] = Query(
        default=20,
        description="Număr maxim de iteme de sincronizat/extras",
    ),
    db: Session = Depends(get_db),
):
    items = await sync_and_get_category(
        category_slug=category_name,
        db=db,
        wiki_client=wiki_client,
        limit=limit,
    )

    return {
        "category": category_name.lower(),
        "total": len(items),
        "items": items,
    }


@app.get("/api/wiki/items/search")
async def search_items(
    q: str = Query(..., description="Cuvânt cheie pentru căutare"),
    category: Optional[str] = Query(
        None, description="Filtrează opțional după categorie"
    ),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(WikiItemModel).where(
        or_(
            WikiItemModel.name.ilike(f"%{q}%"),
            WikiItemModel.spawn_command.ilike(f"%{q}%"),
            WikiItemModel.gfi.ilike(f"%{q}%"),
        )
    )

    if category:
        stmt = stmt.where(WikiItemModel.category.ilike(f"%{category}%"))

    result = await db.execute(stmt)
    results = result.scalars().all()

    return {"count": len(results), "items": results}

@app.get("/api/wiki/search")
async def search_items(
    q: str = Query(
        ..., min_length=2, description="Cuvântul cheie pentru căutare"
    ),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
):
    # Pregătim termenul pentru ILIKE (ex: "%berry%" va potrivi "Amarberry", "Berry Juice", etc.)
    search_term = f"%{q}%"

    # Construim interogarea cu OR între proprietăți
    stmt = (
        select(WikiItemModel)
        .where(
            or_(
                WikiItemModel.name.ilike(search_term),
                WikiItemModel.description.ilike(search_term),
                WikiItemModel.category.ilike(search_term),
                WikiItemModel.gfi.ilike(search_term),
                WikiItemModel.spawn_command.ilike(search_term),
            )
        )
        .limit(limit)
    )

    result = await db.execute(stmt)
    items = result.scalars().all()

    return items