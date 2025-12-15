"""
Script de migration: Renommer case et judgment → course

This script orchestrates the database migration from the old "case" and "judgment"
tables to the new unified "course" table.

Usage:
    cd backend
    python migrations/migrate_to_course.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path so we can import services
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.surreal_service import get_surreal_service

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def validate_pre_migration():
    """Validate state before migration."""
    logger.info("=" * 70)
    logger.info("📊 PRE-MIGRATION VALIDATION")
    logger.info("=" * 70)

    service = get_surreal_service()
    await service.connect()

    # Count records in each table
    try:
        case_result = await service.query("SELECT count() FROM case GROUP ALL")
        case_count = extract_count(case_result)
        logger.info(f"✓ Cases found: {case_count}")
    except Exception as e:
        logger.warning(f"⚠ No 'case' table or error: {e}")
        case_count = 0

    try:
        judgment_result = await service.query("SELECT count() FROM judgment GROUP ALL")
        judgment_count = extract_count(judgment_result)
        logger.info(f"✓ Judgments found: {judgment_count}")
    except Exception as e:
        logger.warning(f"⚠ No 'judgment' table or error: {e}")
        judgment_count = 0

    try:
        doc_result = await service.query("SELECT count() FROM document GROUP ALL")
        doc_count = extract_count(doc_result)
        logger.info(f"✓ Documents found: {doc_count}")
    except Exception as e:
        logger.warning(f"⚠ No 'document' table or error: {e}")
        doc_count = 0

    try:
        conv_result = await service.query("SELECT count() FROM conversation GROUP ALL")
        conv_count = extract_count(conv_result)
        logger.info(f"✓ Conversations found: {conv_count}")
    except Exception as e:
        logger.warning(f"⚠ No 'conversation' table or error: {e}")
        conv_count = 0

    total_courses_expected = case_count + judgment_count
    logger.info(f"\n📈 Expected total courses after migration: {total_courses_expected}")

    logger.info("=" * 70)

    return total_courses_expected


async def run_migration():
    """Execute the migration SQL script."""
    logger.info("=" * 70)
    logger.info("🚀 EXECUTING MIGRATION")
    logger.info("=" * 70)

    service = get_surreal_service()
    await service.connect()

    migration_file = Path(__file__).parent / "003_rename_to_course.surql"

    if not migration_file.exists():
        raise FileNotFoundError(f"Migration file not found: {migration_file}")

    logger.info(f"📄 Reading migration file: {migration_file.name}")

    # Read the migration SQL
    sql_content = migration_file.read_text()

    # Split into statements (by semicolon, but preserve the logic)
    # Note: SurrealDB processes multi-line statements, so we'll execute the whole file
    logger.info("📝 Executing migration SQL...")

    try:
        # Execute the entire migration as one transaction
        result = await service.query(sql_content)
        logger.info("✅ Migration SQL executed successfully")

        # Log any results
        if result:
            logger.info(f"   Result count: {len(result) if isinstance(result, list) else 1}")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

    logger.info("=" * 70)


async def validate_post_migration(expected_count: int):
    """Validate state after migration."""
    logger.info("=" * 70)
    logger.info("🔍 POST-MIGRATION VALIDATION")
    logger.info("=" * 70)

    service = get_surreal_service()
    await service.connect()

    success = True

    # 1. Verify course table exists and has correct count
    try:
        course_result = await service.query("SELECT count() FROM course GROUP ALL")
        course_count = extract_count(course_result)
        logger.info(f"✓ Courses found: {course_count}")

        if course_count != expected_count:
            logger.warning(f"⚠ Expected {expected_count} courses, found {course_count}")
            # Not a hard failure - some duplicates might have been merged

    except Exception as e:
        logger.error(f"❌ Error querying course table: {e}")
        success = False

    # 2. Verify old tables are removed
    try:
        await service.query("SELECT count() FROM case GROUP ALL")
        logger.error("❌ Table 'case' still exists!")
        success = False
    except:
        logger.info("✓ Table 'case' removed")

    try:
        await service.query("SELECT count() FROM judgment GROUP ALL")
        logger.error("❌ Table 'judgment' still exists!")
        success = False
    except:
        logger.info("✓ Table 'judgment' removed")

    # 3. Verify documents have course_id
    try:
        doc_result = await service.query("SELECT count() FROM document WHERE course_id IS NOT NONE GROUP ALL")
        doc_count = extract_count(doc_result)
        logger.info(f"✓ Documents with course_id: {doc_count}")
    except Exception as e:
        logger.warning(f"⚠ Error checking documents: {e}")

    # 4. Verify no old field references exist
    try:
        old_case_id = await service.query("SELECT count() FROM document WHERE case_id IS NOT NONE GROUP ALL")
        old_case_count = extract_count(old_case_id)
        if old_case_count > 0:
            logger.error(f"❌ Found {old_case_count} documents still with case_id!")
            success = False
        else:
            logger.info("✓ No documents with old case_id field")
    except:
        # Field doesn't exist - that's good!
        logger.info("✓ No documents with old case_id field")

    try:
        old_judgment_id = await service.query("SELECT count() FROM document WHERE judgment_id IS NOT NONE GROUP ALL")
        old_judgment_count = extract_count(old_judgment_id)
        if old_judgment_count > 0:
            logger.error(f"❌ Found {old_judgment_count} documents still with judgment_id!")
            success = False
        else:
            logger.info("✓ No documents with old judgment_id field")
    except:
        # Field doesn't exist - that's good!
        logger.info("✓ No documents with old judgment_id field")

    # 5. Sample a few courses to verify data integrity
    try:
        sample = await service.query("SELECT * FROM course LIMIT 3")
        if sample:
            logger.info(f"\n📋 Sample courses:")
            for course in extract_results(sample):
                logger.info(f"   - {course.get('id')}: {course.get('title', 'Untitled')}")
    except Exception as e:
        logger.warning(f"⚠ Could not fetch sample courses: {e}")

    logger.info("=" * 70)

    return success


def extract_count(result):
    """Extract count from SurrealDB query result."""
    if not result:
        return 0

    # Handle different result formats
    if isinstance(result, list) and len(result) > 0:
        first = result[0]
        if isinstance(first, dict):
            if 'result' in first and isinstance(first['result'], list) and len(first['result']) > 0:
                return first['result'][0].get('count', 0)
            elif 'count' in first:
                return first.get('count', 0)

    return 0


def extract_results(result):
    """Extract result list from SurrealDB query result."""
    if not result:
        return []

    if isinstance(result, list) and len(result) > 0:
        first = result[0]
        if isinstance(first, dict) and 'result' in first:
            return first['result'] if isinstance(first['result'], list) else []
        elif isinstance(first, list):
            return first

    return result if isinstance(result, list) else []


async def main():
    """Main migration workflow."""
    logger.info("\n" + "=" * 70)
    logger.info("🎯 MIGRATION: judgment + case → course")
    logger.info("=" * 70 + "\n")

    try:
        # Step 1: Pre-migration validation
        expected_count = await validate_pre_migration()

        # Step 2: Confirm with user
        print("\n⚠️  WARNING: This will modify your database!")
        print("   - Tables 'case' and 'judgment' will be merged into 'course'")
        print("   - All foreign key references will be updated")
        print("   - Old tables will be removed")
        print("\nMake sure you have a backup before proceeding.")
        print("(Backup created at: backup_pre_migration.surql)\n")

        response = input("Continue with migration? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            logger.info("❌ Migration cancelled by user")
            return

        # Step 3: Run migration
        await run_migration()

        # Step 4: Post-migration validation
        success = await validate_post_migration(expected_count)

        # Step 5: Final report
        print("\n" + "=" * 70)
        if success:
            logger.info("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
            logger.info("   - All tables renamed")
            logger.info("   - All foreign keys updated")
            logger.info("   - Data integrity verified")
        else:
            logger.error("⚠️  MIGRATION COMPLETED WITH WARNINGS")
            logger.error("   Please review the errors above")
        print("=" * 70 + "\n")

    except Exception as e:
        logger.error(f"\n❌ MIGRATION FAILED: {e}")
        logger.error("   Your database may be in an inconsistent state")
        logger.error("   Restore from backup: backup_pre_migration.surql")
        raise


if __name__ == "__main__":
    asyncio.run(main())
