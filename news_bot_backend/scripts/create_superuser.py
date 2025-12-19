import asyncio
import sys
from pathlib import Path
import argparse

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.models import User
from app.services.security import hash_password


async def create_superuser(
        username: str,
        email: str,
        password: str,
        first_name: str | None = None,
        last_name: str | None = None
):
    async with AsyncSessionLocal() as session:
        try:
            # Проверяем, существует ли пользователь с таким username или email
            result = await session.execute(
                select(User).where(
                    (User.username == username) | (User.email == email)
                )
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"❌ Пользователь с username '{username}' или email '{email}' уже существует!")
                print(f"   ID: {existing_user.id}, is_super: {existing_user.is_super}")

                # Спрашиваем, хотим ли сделать существующего пользователя superuser
                if not existing_user.is_super:
                    response = input(f"   Сделать пользователя '{username}' superuser? (y/n): ")
                    if response.lower() == 'y':
                        existing_user.is_super = True
                        existing_user.is_verified = True
                        await session.commit()
                        print(f"✅ Пользователь '{username}' теперь superuser!")
                    else:
                        print("Отменено.")
                return

            # Создаём нового superuser
            hashed_password = hash_password(password)

            new_user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                first_name=first_name,
                last_name=last_name,
                is_super=True,
                scan_period=3
            )

            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)

            print(f"✅ Superuser успешно создан!")
            print(f"   ID: {new_user.id}")
            print(f"   Username: {new_user.username}")
            print(f"   Email: {new_user.email}")
            print(f"   is_super: {new_user.is_super}")
            print(f"   is_verified: {new_user.is_verified}")

        except Exception as e:
            await session.rollback()
            print(f"❌ Ошибка при создании superuser: {str(e)}")
            raise


async def main():
    parser = argparse.ArgumentParser(description="Создать superuser для News Bot")
    parser.add_argument("--username", type=str, help="Username для superuser")
    parser.add_argument("--email", type=str, help="Email для superuser")
    parser.add_argument("--password", type=str, help="Password для superuser")
    parser.add_argument("--first-name", type=str, help="Имя (опционально)")
    parser.add_argument("--last-name", type=str, help="Фамилия (опционально)")

    args = parser.parse_args()

    # Если аргументы не переданы, используем интерактивный режим
    if not args.username or not args.email or not args.password:
        print("=== Создание Superuser для News Bot ===\n")

        username = args.username or input("Username: ").strip()
        if not username:
            print("❌ Username обязателен!")
            return

        email = args.email or input("Email: ").strip()
        if not email:
            print("❌ Email обязателен!")
            return

        password = args.password or input("Password: ").strip()
        if not password:
            print("❌ Password обязателен!")
            return

        if len(password) < 8:
            print("⚠️  Пароль должен быть минимум 8 символов!")
            confirm = input("Продолжить? (y/n): ")
            if confirm.lower() != 'y':
                return

        first_name = args.first_name or input("First name: ").strip() or None
        last_name = args.last_name or input("Last name: ").strip() or None
    else:
        username = args.username
        email = args.email
        password = args.password
        first_name = args.first_name
        last_name = args.last_name

    await create_superuser(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name
    )


if __name__ == "__main__":
    asyncio.run(main())

'''
To execute script, firstly run docker containers. 
Then run command in console in directory news_bot_backend:

docker-compose exec api python scripts/create_superuser.py

'''
