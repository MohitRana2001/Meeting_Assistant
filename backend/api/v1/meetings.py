"""
Phase 1 provides a placeholder route returning a static list.

Phase 3 will query DB and Phase 4 will enrich with agent output.
"""

from fastapi import APIRouter
from typing import List, Dict, Union

router = APIRouter(prefix="/meetings")


@router.get("/summaries")
async def list_summaries() -> List[Dict[str, Union[str, List[str]]]]:
    # --- Phase 1 dummy payload ---
    return [
        {"id": "sample-1", "title": "Kick-off call", "tasks": []},
        {"id": "sample-2", "title": "Sprint review", "tasks": ["Refactor API"]},
    ]
