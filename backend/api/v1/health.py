from fastapi import APIRouter

router = APIRouter()


@router.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}
