from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.source import Source
from app.schemas.source import SourceCreate, SourceRead, SourceUpdate

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/", response_model=list[SourceRead])
async def list_sources(db: AsyncSession = Depends(get_db)) -> list[SourceRead]:
    result = await db.execute(select(Source))
    sources = result.scalars().all()
    return [SourceRead.model_validate(source) for source in sources]


@router.post("/", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
async def create_source(payload: SourceCreate, db: AsyncSession = Depends(get_db)) -> SourceRead:
    exists = await db.execute(select(Source).where(Source.source_url == payload.source_url))
    if exists.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source with this URL already exists",
        )

    source = Source(**payload.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return SourceRead.model_validate(source)


@router.get("/{source_id}", response_model=SourceRead)
async def get_source(source_id: int, db: AsyncSession = Depends(get_db)) -> SourceRead:
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return SourceRead.model_validate(source)


@router.patch("/{source_id}", response_model=SourceRead)
async def update_source(
    source_id: int,
    payload: SourceUpdate,
    db: AsyncSession = Depends(get_db),
) -> SourceRead:
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return SourceRead.model_validate(source)

    new_url = data.get("source_url")
    if new_url and new_url != source.source_url:
        exists = await db.execute(select(Source).where(Source.source_url == new_url))
        if exists.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source with this URL already exists",
            )

    for key, value in data.items():
        setattr(source, key, value)

    await db.commit()
    await db.refresh(source)
    return SourceRead.model_validate(source)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)) -> None:
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    await db.delete(source)
    await db.commit()
