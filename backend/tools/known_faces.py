"""Known Faces DB: simple JSON name matching."""

import json
from pathlib import Path


KNOWN_FACES_PATH = Path(__file__).parent.parent.parent / "data" / "known_faces.json"


async def check_known_faces(name: str = "") -> dict:
    """Check if a visitor name matches a registered known person."""
    if not name:
        return {"found": False, "message": "No name provided"}

    try:
        data = json.loads(KNOWN_FACES_PATH.read_text())
    except FileNotFoundError:
        return {"found": False, "message": "Known faces database not found"}

    name_lower = name.strip().lower()
    for person in data:
        if person["name"].lower() == name_lower:
            return {
                "found": True,
                "name": person["name"],
                "relation": person["relation"],
                "memo": person.get("memo", ""),
            }

    return {"found": False, "message": f"'{name}' is not a registered known person"}
