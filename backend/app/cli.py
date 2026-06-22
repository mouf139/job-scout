import asyncio

import click
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, engine, Base
from app.models.user import User, UserRole
from app.services.auth import hash_password


async def _create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _create_admin(name: str, email: str, password: str):
    await _create_tables()
    async with async_session() as db:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            click.echo(f"User with email {email} already exists.")
            return

        user = User(
            name=name,
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.admin,
            must_change_password=False,
            onboarding_completed=True,
        )
        db.add(user)
        await db.commit()
        click.echo(f"Admin user '{name}' created successfully.")


@click.group()
def cli():
    pass


@cli.command()
@click.option("--name", prompt="Admin name")
@click.option("--email", prompt="Admin email")
@click.option("--password", prompt="Admin password", hide_input=True, confirmation_prompt=True)
def create_admin(name: str, email: str, password: str):
    asyncio.run(_create_admin(name, email, password))


@cli.command()
def init_db():
    asyncio.run(_create_tables())
    click.echo("Database tables created.")


if __name__ == "__main__":
    cli()
