import asyncio
import os
import sys

# Ensure the backend directory is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select

async def verify_user(email: str):
    print(f"Verifying email for user: {email} in Neon database...")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.email_verified = True
            user.email_verification_token = None
            await session.commit()
            print(f"SUCCESS: User {email} is now verified and can log in immediately!")
        else:
            print(f"Error: User {email} not found in database. Register on the frontend first.")

if __name__ == "__main__":
    target_email = sys.argv[1] if len(sys.argv) > 1 else "adityamishrav820@gmail.com"
    asyncio.run(verify_user(target_email))

