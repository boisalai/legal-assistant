#!/usr/bin/env python3
"""
Script de récupération d'un cours après corruption de la base de données.

Ce script :
1. Scanne le répertoire uploads/ d'un cours
2. Recrée le cours en base de données
3. Réenregistre tous les documents trouvés

Usage:
    python scripts/recover_course.py <course_id>
    python scripts/recover_course.py 94921feb
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.surreal_service import SurrealDBService
from config.settings import settings


async def recover_course(course_id: str):
    """Récupère un cours à partir des fichiers sur disque."""

    print(f"🔧 Récupération du cours {course_id}")
    print("=" * 70)

    # Chemins
    uploads_dir = Path(settings.upload_dir) / course_id
    if not uploads_dir.exists():
        print(f"❌ Répertoire non trouvé: {uploads_dir}")
        return

    # Connexion à la base de données
    surreal_service = SurrealDBService(
        url="ws://localhost:8002/rpc",
        namespace="legal_assistant",
        database="legal_assistant"
    )
    await surreal_service.connect()

    # Vérifier si le cours existe
    result = await surreal_service.query(
        "SELECT * FROM course WHERE id = $course_id",
        {"course_id": f"course:{course_id}"}
    )

    course_exists = result and result[0].get("result")

    if not course_exists:
        print(f"⚠️  Le cours n'existe pas en base. Création...")

        # Créer le cours
        await surreal_service.query(
            """
            CREATE course CONTENT {
                id: type::thing("course", $course_id),
                title: $title,
                description: $description,
                course_code: $course_code,
                professor: $professor,
                credits: $credits,
                color: $color,
                keywords: [],
                pinned: false,
                created_at: $now,
                updated_at: $now
            }
            """,
            {
                "course_id": course_id,
                "title": "Cours récupéré",
                "description": "Cours récupéré automatiquement",
                "course_code": "",
                "professor": "",
                "credits": 3,
                "color": "#3B82F6",
                "now": datetime.now().isoformat()
            }
        )
        print(f"✅ Cours créé: course:{course_id}")
    else:
        print(f"✅ Le cours existe déjà en base")

    # Scanner les fichiers
    print(f"\n📂 Scan du répertoire: {uploads_dir}")
    all_files = list(uploads_dir.glob("*"))
    pdf_files = [f for f in all_files if f.suffix.lower() == ".pdf"]
    md_files = [f for f in all_files if f.suffix.lower() == ".md"]
    other_files = [f for f in all_files if f not in pdf_files and f not in md_files]

    print(f"   Trouvé:")
    print(f"   - {len(pdf_files)} fichiers PDF")
    print(f"   - {len(md_files)} fichiers Markdown")
    print(f"   - {len(other_files)} autres fichiers")

    # Réenregistrer les fichiers
    print(f"\n📝 Réenregistrement des fichiers...")

    registered_count = 0
    skipped_count = 0

    for file_path in all_files:
        if file_path.is_dir():
            continue

        # ID du document = nom du fichier sans extension
        doc_id = file_path.stem

        # Vérifier si le document existe déjà
        result = await surreal_service.query(
            "SELECT id FROM document WHERE id = $doc_id",
            {"doc_id": f"document:{doc_id}"}
        )

        if result and result[0].get("result"):
            print(f"   ⏭️  Existe déjà: {file_path.name}")
            skipped_count += 1
            continue

        # Créer l'enregistrement
        mime_type = f"application/{file_path.suffix.lstrip('.')}"
        if file_path.suffix.lower() == ".pdf":
            mime_type = "application/pdf"
        elif file_path.suffix.lower() == ".md":
            mime_type = "text/markdown"

        try:
            await surreal_service.query(
                """
                CREATE document CONTENT {
                    id: type::thing("document", $doc_id),
                    course_id: type::thing("course", $course_id),
                    filename: $filename,
                    file_type: $file_type,
                    mime_type: $mime_type,
                    size: $size,
                    file_path: $file_path,
                    created_at: $now,
                    file_exists: true
                }
                """,
                {
                    "doc_id": doc_id,
                    "course_id": course_id,
                    "filename": file_path.name,
                    "file_type": file_path.suffix.lstrip("."),
                    "mime_type": mime_type,
                    "size": file_path.stat().st_size,
                    "file_path": str(file_path),
                    "now": datetime.now().isoformat()
                }
            )
            print(f"   ✅ Enregistré: {file_path.name}")
            registered_count += 1
        except Exception as e:
            print(f"   ❌ Erreur: {file_path.name} - {e}")

    print(f"\n📊 Résumé:")
    print(f"   ✅ Enregistrés: {registered_count} documents")
    print(f"   ⏭️  Déjà existants: {skipped_count} documents")
    print(f"   📄 Total: {len([f for f in all_files if f.is_file()])} fichiers")

    print(f"\n💡 Prochaines étapes:")
    print(f"   1. Rafraîchissez la page du cours dans votre navigateur")
    print(f"   2. Les documents PDF devraient être visibles")
    print(f"   3. Utilisez 'Extraire en markdown' pour générer les fichiers .md")
    print(f"   4. Le texte sera automatiquement nettoyé des null bytes")

    # Fermer la connexion pour flush les changements
    await surreal_service.disconnect()

    print(f"\n✅ Récupération terminée!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/recover_course.py <course_id>")
        print("Exemple: python scripts/recover_course.py 94921feb")
        sys.exit(1)

    course_id = sys.argv[1]
    asyncio.run(recover_course(course_id))
