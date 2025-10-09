from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.db.database import get_db
from app.models.testmodel import TestTable
from app.schemas.testschema import TestCreate

router=APIRouter(prefix='/test')

@router.post("/create/")
async def test_create(test: TestCreate, db: AsyncSession=Depends(get_db)):
    new_test=TestTable(**test.model_dump())
    db.add(new_test)
    await db.commit()
    await db.refresh(new_test)
    return {"message": "Test item created"}

@router.get("/test_id/")
async def get_test(test_id: int, db: AsyncSession=Depends(get_db)):
    result = await db.execute(select(TestTable).where(TestTable.id == test_id))
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"test with id {test_id} not found"
        )
    return test