"""
Script to create academic sessions for years 2025-2032.
Creates Automne, Hiver, and Été sessions for each year.
"""

import asyncio
from datetime import datetime
from services.session_service import SessionService
from services.surreal_service import init_surreal_service
from models.session import SessionCreate


async def create_all_sessions():
    """Create academic sessions for years 2025-2032."""

    # Initialize global SurrealDB service
    surreal_service = init_surreal_service(
        url="ws://localhost:8002/rpc",
        namespace="legal",
        database="legal_db",
        username="root",
        password="root"
    )
    await surreal_service.connect()

    # Initialize session service (uses global service)
    session_service = SessionService()

    sessions_to_create = []

    # Define semester date ranges
    semester_config = {
        "Automne": {
            "start_month": 9,  # September
            "start_day": 1,
            "end_month": 12,   # December
            "end_day": 31,
        },
        "Hiver": {
            "start_month": 1,  # January
            "start_day": 1,
            "end_month": 4,    # April
            "end_day": 30,
        },
        "Été": {
            "start_month": 5,  # May
            "start_day": 1,
            "end_month": 8,    # August
            "end_day": 31,
        },
    }

    # Generate sessions for years 2025-2032
    for year in range(2025, 2033):  # 2025 to 2032 inclusive
        for semester_name, dates in semester_config.items():
            title = f"{semester_name} {year}"
            start_date = datetime(year, dates["start_month"], dates["start_day"])
            end_date = datetime(year, dates["end_month"], dates["end_day"])

            session_data = SessionCreate(
                title=title,
                semester=semester_name,
                year=year,
                start_date=start_date,
                end_date=end_date,
            )

            sessions_to_create.append(session_data)

    # Create all sessions
    print(f"Creating {len(sessions_to_create)} sessions...")
    created_count = 0

    for session_data in sessions_to_create:
        try:
            created_session = await session_service.create_session(session_data)
            print(f"✓ Created: {created_session.title} ({created_session.id})")
            created_count += 1
        except Exception as e:
            print(f"✗ Failed to create {session_data.title}: {e}")

    print(f"\n✅ Successfully created {created_count}/{len(sessions_to_create)} sessions")

    # List all sessions to verify
    print("\n📋 All sessions in database:")
    all_sessions = await session_service.list_sessions(page=1, page_size=100)
    for session in all_sessions.items:
        print(f"  - {session.title}")

    # Close connection
    await surreal_service.disconnect()


if __name__ == "__main__":
    asyncio.run(create_all_sessions())
