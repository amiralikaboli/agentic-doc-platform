#!/usr/bin/env python
"""Initialize database: create DB, enable pgvector, and create all tables from models."""

import asyncio
import os
import sys
from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.models import Base
from src.core.config import settings


async def init_db():
    """Create database, pgvector extension, and all tables."""
    
    # Step 1: Connect to default 'postgres' DB to create the target DB
    print("Step 1: Creating database...")
    # Replace only the database name, not the driver name
    postgres_url = settings.DB_URL.rsplit("/", 1)[0] + "/postgres"
    # Convert async URL to sync for admin operations
    sync_postgres_url = postgres_url.replace("postgresql+asyncpg", "postgresql")
    
    try:
        # Use isolation_level=0 for autocommit mode
        sync_engine = create_engine(
            sync_postgres_url,
            echo=False,
            isolation_level="AUTOCOMMIT"
        )
        with sync_engine.connect() as conn:
            try:
                conn.execute(text(f"CREATE DATABASE {settings.DB_NAME};"))
                print(f"✓ Database '{settings.DB_NAME}' created")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"✓ Database '{settings.DB_NAME}' already exists")
                else:
                    raise
        sync_engine.dispose()
    except Exception as e:
        print(f"✗ Failed to create database: {e}")
        raise
    
    # Step 2: Connect to target DB and enable pgvector
    print("Step 2: Enabling pgvector extension...")
    target_db_url = settings.DB_URL.replace("postgresql+asyncpg", "postgresql")
    sync_engine = create_engine(
        target_db_url,
        echo=False,
        isolation_level="AUTOCOMMIT"
    )
    with sync_engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            print("✓ pgvector extension enabled")
        except Exception as e:
            print(f"✗ Failed to enable pgvector: {e}")
            raise
    sync_engine.dispose()
    
    # Step 3: Create tables from SQLAlchemy models
    print("Step 3: Creating tables from models...")
    async_engine = create_async_engine(settings.DB_URL, echo=False)
    
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await async_engine.dispose()
    print("✓ All tables created successfully")
    print("✓ Database initialization complete!")


if __name__ == "__main__":
    try:
        asyncio.run(init_db())
        sys.exit(0)
    except Exception as e:
        print(f"✗ Database initialization failed: {e}", file=sys.stderr)
        sys.exit(1)
