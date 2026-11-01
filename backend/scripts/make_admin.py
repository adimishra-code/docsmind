import asyncio
import os
import sys

# Ensure the backend directory is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select

async def make_admin(email: str):
    print(f"Attempting to make user {email} an admin...")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.is_admin = True
            await session.commit()
            print(f"Success! User {email} is now an admin.")
        else:
            print(f"Error: User {email} not found in the database. Please register on the frontend first.")

if __name__ == "__main__":
    email_to_make_admin = "adityamishrav820@gmail.com"
    asyncio.run(make_admin(email_to_make_admin))
