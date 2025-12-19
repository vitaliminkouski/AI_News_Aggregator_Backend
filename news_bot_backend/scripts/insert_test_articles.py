import asyncio
import json
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal  # Adjust import based on your actual path
from app.models import Topic, Source, Articles


async def seed_db():
    async with AsyncSessionLocal() as session:
        try:
            with open("scripts/test_articles.json", "r", encoding="utf-8") as f:
                data = json.load(f)

            print("Starting database seeding...")

            for a_data in data["articles"]:
                stmt = select(Articles).where(Articles.title == a_data["title"])
                result = await session.execute(stmt)
                if not result.scalar_one_or_none():
                    article = Articles(
                        title=a_data["title"],
                        summary=a_data["summary"],
                        published_at=datetime.fromisoformat(a_data["published_at"]),
                        source_id=a_data["source_id"],
                        topic_id=a_data["topic_id"]
                    )
                    session.add(article)

            await session.commit()
            print(f"Added {len(data['articles'])} articles.")
            print("Seeding completed successfully!")

        except Exception as e:
            await session.rollback()
            print(f"An error occurred: {e}")
        finally:
            await session.close()


if __name__ == "__main__":
    asyncio.run(seed_db())
