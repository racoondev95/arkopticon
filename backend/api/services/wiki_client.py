import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import WikiItemModel

CATEGORY_MAPPING = {
    "food": "Food",
    "weapons": "Weapons",
    "buildings": "Structures",
    "structures": "Structures",
    "saddles": "Saddles",
    "armor": "Armor",
    "tools": "Tools",
    "rifles": "Weapons",
}


class ArkWikiClient:
    BASE_URL = "https://ark.wiki.gg"
    API_URL = "https://ark.wiki.gg/api.php"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def process_spawn_commands(self, item: Dict[str, Any]) -> None:
        """Procesează și curăță comanda de spawn."""
        command = item.get("spawn_command")

        if not command or not isinstance(command, str):
            item["spawn_command_short"] = None
            item["spawn_command_long"] = None
            return

        cleaned = command.replace("\xa0", " ")
        cleaned = re.sub(r"([^\s])or", r"\1 or", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"or([^\s])", r"or \1", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        item["spawn_command"] = cleaned
        parts = re.split(r"\s+or\s+", cleaned, maxsplit=1, flags=re.IGNORECASE)

        if len(parts) == 2:
            item["spawn_command_short"] = parts[0].strip()
            item["spawn_command_long"] = parts[1].strip()
        else:
            item["spawn_command_short"] = cleaned
            item["spawn_command_long"] = None

    async def get_category_links_from_table(
        self, category_page: str
    ) -> List[Dict[str, str]]:
        """Extrage lista de iteme de pe o pagină de categorie de pe wiki."""
        params = {
            "action": "parse",
            "page": category_page,
            "prop": "text",
            "format": "json",
        }

        async with httpx.AsyncClient(
            headers=self.headers, timeout=20.0
        ) as client:
            resp = await client.get(self.API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                raise Exception(data["error"].get("info", "Pagina nu există."))

            html_content = data.get("parse", {}).get("text", {}).get("*", "")
            soup = BeautifulSoup(html_content, "html.parser")

            items_basic = []
            seen_titles = set()

            for table in soup.find_all("table", class_="wikitable"):
                for row in table.find_all("tr"):
                    first_cell = row.find("td")
                    if not first_cell:
                        continue

                    link = first_cell.find("a", href=True)
                    if link and link.get("title"):
                        title = link["title"].strip()
                        href = link["href"]

                        if ":" not in title and title not in seen_titles:
                            seen_titles.add(title)
                            items_basic.append(
                                {
                                    "title": title,
                                    "wiki_url": (
                                        f"{self.BASE_URL}{href}"
                                        if href.startswith("/")
                                        else href
                                    ),
                                }
                            )

            return items_basic

    async def scrape_single_item_details(
        self, page_title: str
    ) -> Dict[str, Any]:
        """Extrage detaliile individuale ale unui item."""
        params = {
            "action": "parse",
            "page": page_title,
            "prop": "text",
            "format": "json",
        }

        async with httpx.AsyncClient(
            headers=self.headers, timeout=15.0
        ) as client:
            resp = await client.get(self.API_URL, params=params)
            if resp.status_code != 200:
                return {}

            data = resp.json()
            if "error" in data:
                return {}

            html_content = data.get("parse", {}).get("text", {}).get("*", "")
            soup = BeautifulSoup(html_content, "html.parser")

            details = {
                "title": page_title,
                "description": None,
                "spawn_command": None,
                "gfi": None,
                "blueprint": None,
            }

            for p in soup.find_all("p"):
                text = p.text.strip()
                if text and len(text) > 15:
                    details["description"] = text
                    break

            spawn_elem = (
                soup.find(class_=lambda c: c and "spawn-command" in c.lower())
                if soup
                else None
            )
            if spawn_elem:
                details["spawn_command"] = spawn_elem.text.strip()

            infobox = soup.find(
                class_=lambda c: c
                and ("infobox" in c.lower() or "portable-infobox" in c.lower())
            )
            if infobox:
                for row in infobox.find_all(
                    ["tr", "div"],
                    class_=lambda c: (
                        c and ("row" in c.lower() or "data" in c.lower())
                        if c
                        else True
                    ),
                ):
                    text_content = row.text.strip()

                    if "GFI" in text_content or "gfi" in text_content:
                        code_tag = row.find("code") or row.find("span")
                        if code_tag:
                            gfi_code = code_tag.text.strip()
                            details["gfi"] = gfi_code
                            if not details["spawn_command"]:
                                details["spawn_command"] = (
                                    f"cheat gfi {gfi_code} 1 1 0"
                                )

                    if "Blueprint" in text_content:
                        code_tag = row.find("code") or row.find("span")
                        if code_tag:
                            details["blueprint"] = code_tag.text.strip()

            if not details["gfi"]:
                fallback_gfi = page_title.replace(" ", "")
                details["gfi"] = fallback_gfi
                if not details["spawn_command"]:
                    details["spawn_command"] = f"cheat gfi {fallback_gfi} 1 1 0"

            return details


async def sync_and_get_category(
    category_slug: str,
    db: AsyncSession,  # Folosim AsyncSession
    wiki_client: ArkWikiClient,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    slug_clean = category_slug.lower().strip()
    wiki_page_title = CATEGORY_MAPPING.get(
        slug_clean, category_slug.capitalize()
    )

    try:
        wiki_links = await wiki_client.get_category_links_from_table(
            wiki_page_title
        )
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Nu s-a putut încărca categoria '{category_slug}'. Eroare Wiki: {str(e)}",
        )

    if limit:
        wiki_links = wiki_links[:limit]

    needed_titles = [item["title"] for item in wiki_links]

    # Interogare asincronă corectă (select în loc de db.query)
    stmt = select(WikiItemModel).where(
        WikiItemModel.category == wiki_page_title,
        WikiItemModel.name.in_(needed_titles),
    )
    result = await db.execute(stmt)
    existing_items = result.scalars().all()

    existing_map = {item.name: item for item in existing_items}

    final_results = []
    items_to_scrape = []

    for link_info in wiki_links:
        title = link_info["title"]

        if title in existing_map:
            db_obj = existing_map[title]
            final_results.append(
                {
                    "name": db_obj.name,
                    "category": db_obj.category,
                    "wiki_url": db_obj.wiki_url,
                    "description": db_obj.description,
                    "spawn_command": db_obj.spawn_command,
                    "spawn_command_short": db_obj.spawn_command_short,
                    "spawn_command_long": db_obj.spawn_command_long,
                    "gfi": db_obj.gfi,
                    "blueprint": db_obj.blueprint,
                }
            )
        else:
            items_to_scrape.append(link_info)

    if items_to_scrape:
        new_models_to_save = []

        for item_info in items_to_scrape:
            title = item_info["title"]
            details = await wiki_client.scrape_single_item_details(title)

            item_dict = {
                "name": title,
                "category": wiki_page_title,
                "wiki_url": item_info["wiki_url"],
                "description": details.get("description"),
                "spawn_command": details.get("spawn_command"),
                "gfi": details.get("gfi"),
                "blueprint": details.get("blueprint"),
            }

            wiki_client.process_spawn_commands(item_dict)

            db_model = WikiItemModel(
                name=item_dict["name"],
                category=item_dict["category"],
                wiki_url=item_dict["wiki_url"],
                description=item_dict["description"],
                spawn_command=item_dict["spawn_command"],
                spawn_command_short=item_dict["spawn_command_short"],
                spawn_command_long=item_dict["spawn_command_long"],
                gfi=item_dict["gfi"],
                blueprint=item_dict["blueprint"],
            )

            new_models_to_save.append(db_model)
            final_results.append(item_dict)

        db.add_all(new_models_to_save)
        await db.commit()  # commit asincron

    return final_results