from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from database import engine, Base, get_db
import models

app = FastAPI(title="Arkopticon API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db():
    # Creează tabelele la pornirea aplicației (dacă nu există)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
def read_root():
    return {"system": "Arkopticon API", "status": "Online"}

@app.get("/items")
async def get_items(db: AsyncSession = Depends(get_db)):
    """Returnează lista de iteme din baza de date."""
    result = await db.execute(select(models.Item))
    items = result.scalars().all()
    return items

@app.get("/test-wiki")
async def test_ark_wiki_api():
    url = "https://ark.wiki.gg/api.php"
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": "Rex",
        "srlimit": 3
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, headers={"User-Agent": "ArkopticonApp/1.0"})
            data = response.json()
            return {
                "success": True,
                "search_results": data.get("query", {}).get("search", [])
            }
        except Exception as e:
            return {"success": False, "error": str(e)}