import asyncio

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.models import Source, Articles, User, UserSources


async def insert_test_sources():
    async with AsyncSessionLocal() as db:
        test_sources = [
            {
                "source_name": "test source 1",
                "source_url": "https://test_source_1.com",
                "language": "en"
            },
            {
                "source_name": "test source 2",
                "source_url": "https://test_source_2.com",
                "language": "ru"
            }
        ]

        for source_data in test_sources:
            new_source = Source(
                source_name=source_data.get("source_name"),
                source_url=source_data.get('source_url'),
                language=source_data.get("language")
            )

            db.add(new_source)
            await db.commit()
            await db.refresh(new_source)


async def insert_test_articles():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Source))
        sources = res.scalars().all()

        if not sources:
            return

        test_articles_data = [
            {
                "title": "test article 1",
                "summary": "summary for test article 1",
                "source_id": sources[0].id
            },
            {
                "title": "test article 2",
                "summary": "summary for test article 2",
                "source_id": sources[0].id
            },
            {
                "title": "test article 3",
                "summary": "summary for test article 3",
                "source_id": sources[1].id
            }
        ]

        created_articles = []

        for artcl_data in test_articles_data:

            existing = await db.execute(select(Articles).where(Articles.title == artcl_data.get("title")))
            if existing.scalar_one_or_none():
                continue

            new_article = Articles(
                title=artcl_data.get("title"),
                summary=artcl_data.get("summary"),
                source_id=artcl_data.get("source_id")
            )
            db.add(new_article)
            created_articles.append(new_article)

        await db.commit()

        for article in created_articles:
            await db.refresh(article)

async def insert_test_user_sources():
    async with AsyncSessionLocal() as db:
        res=await db.execute(select(User).where(User.username == "user1"))
        user = res.scalar_one_or_none()

        if not user:
            return

        res=await db.execute(select(Source))
        sources=res.scalars().all()

        new_user_source=UserSources(
            user_id=user.id,
            source_id=sources[0].id
        )
        db.add(new_user_source)
        await db.commit()
        await db.refresh(new_user_source)
# asyncio.run(insert_test_sources())
# asyncio.run(insert_test_articles())
asyncio.run(insert_test_user_sources())
