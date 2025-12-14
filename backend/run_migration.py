"""
Script pour exécuter les migrations SurrealDB.

Usage: python run_migration.py <migration_file>
"""

import asyncio
import sys
from pathlib import Path

from services.surreal_service import get_surreal_service, init_surreal_service
from config.settings import settings


async def run_migration(migration_file: Path):
    """Execute a migration file on SurrealDB."""

    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False

    print(f"📄 Reading migration file: {migration_file}")
    migration_sql = migration_file.read_text()

    # Initialize and connect to SurrealDB
    print("🔌 Connecting to SurrealDB...")
    service = init_surreal_service(
        url=settings.surreal_url,
        namespace=settings.surreal_namespace,
        database=settings.surreal_database,
        username=settings.surreal_username,
        password=settings.surreal_password,
    )

    try:
        await service.connect()
        print(f"✅ Connected to SurrealDB: {settings.surreal_url}")
        print(f"   Namespace: {settings.surreal_namespace}")
        print(f"   Database: {settings.surreal_database}")
    except Exception as e:
        print(f"❌ Failed to connect to SurrealDB: {e}")
        return False

    # Execute migration
    print("\n🚀 Executing migration...")
    try:
        # Split statements by semicolon and execute each
        statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]

        total = len(statements)
        success_count = 0

        for i, statement in enumerate(statements, 1):
            # Skip comments and empty lines
            if not statement or statement.startswith('--'):
                continue

            print(f"   [{i}/{total}] Executing statement...")
            try:
                result = await service.query(statement)
                success_count += 1
                print(f"   ✅ Success")
            except Exception as e:
                print(f"   ⚠️  Error: {e}")
                print(f"   Statement: {statement[:100]}...")

        print(f"\n✅ Migration completed: {success_count}/{total} statements executed successfully")
        return True

    except Exception as e:
        print(f"❌ Failed to execute migration: {e}")
        return False

    finally:
        await service.disconnect()
        print("🔌 Disconnected from SurrealDB")


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python run_migration.py <migration_file>")
        print("Example: python run_migration.py migrations/002_academic_schema.surql")
        sys.exit(1)

    migration_file = Path(sys.argv[1])
    success = await run_migration(migration_file)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
