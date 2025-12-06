"""
Script de debug pour investiguer la base de données SurrealDB.
"""

import asyncio
from services.surreal_service import SurrealDBService
from config.settings import settings


async def debug_database():
    """Debug database content."""
    service = SurrealDBService(
        url=settings.surreal_url,
        namespace=settings.surreal_namespace,
        database=settings.surreal_database
    )
    await service.connect()

    print(f"✅ Connected to SurrealDB")
    print(f"   URL: {settings.surreal_url}")
    print(f"   Namespace: {settings.surreal_namespace}")
    print(f"   Database: {settings.surreal_database}")
    print()

    # Check database info
    print("=" * 60)
    print("DATABASE INFO")
    print("=" * 60)
    result = await service.query("INFO FOR DB")
    if result:
        info = result[0] if isinstance(result, list) else result
        tables = info.get('tables', {}) if isinstance(info, dict) else {}
        print(f"Tables: {list(tables.keys())}")
    print()

    # Count documents
    print("=" * 60)
    print("DOCUMENT COUNT")
    print("=" * 60)
    result = await service.query("SELECT count() FROM document GROUP ALL")
    if result and len(result) > 0:
        data = result[0].get('result', []) if isinstance(result[0], dict) else result
        count = data[0].get('count', 0) if data else 0
        print(f"Total documents: {count}")
    else:
        print("Total documents: 0")
    print()

    # List all documents
    print("=" * 60)
    print("ALL DOCUMENTS (first 20)")
    print("=" * 60)
    result = await service.query("SELECT id, nom_fichier, case_id, source_type FROM document LIMIT 20")
    if result and len(result) > 0:
        docs = result[0].get('result', []) if isinstance(result[0], dict) else result
        if docs:
            for doc in docs:
                print(f"  {doc.get('id')}")
                print(f"    nom_fichier: {doc.get('nom_fichier')}")
                print(f"    case_id: {doc.get('case_id')}")
                print(f"    source_type: {doc.get('source_type')}")
                print()
        else:
            print("  No documents found")
    else:
        print("  No documents found")
    print()

    # Check cases
    print("=" * 60)
    print("CASES")
    print("=" * 60)
    result = await service.query("SELECT id, nom_dossier FROM case")
    if result and len(result) > 0:
        cases = result[0].get('result', []) if isinstance(result[0], dict) else result
        if cases:
            for case in cases:
                print(f"  {case.get('id')} - {case.get('nom_dossier')}")
        else:
            print("  No cases found")
    else:
        print("  No cases found")
    print()

    # Check if there's a judgment table (legacy)
    print("=" * 60)
    print("LEGACY JUDGMENT TABLE")
    print("=" * 60)
    try:
        result = await service.query("SELECT id, nom_dossier FROM judgment LIMIT 5")
        if result and len(result) > 0:
            judgments = result[0].get('result', []) if isinstance(result[0], dict) else result
            if judgments:
                print(f"  Found {len(judgments)} judgments (LEGACY TABLE!)")
                for j in judgments:
                    print(f"    {j.get('id')} - {j.get('nom_dossier')}")
            else:
                print("  No judgments found")
        else:
            print("  No judgments found")
    except Exception as e:
        print(f"  Error: {e}")


if __name__ == "__main__":
    asyncio.run(debug_database())
