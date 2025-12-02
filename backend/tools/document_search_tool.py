"""
Document search tool for the Agno agent.

This tool allows the AI agent to search through documents in a case.
"""

import logging
import re
from typing import Optional, List
from pathlib import Path

from agno.tools import tool

from services.surreal_service import get_surreal_service

logger = logging.getLogger(__name__)


async def _get_case_documents(judgment_id: str) -> List[dict]:
    """
    Get all documents for a case with their content.

    Args:
        judgment_id: ID of the case

    Returns:
        List of document dicts with texte_extrait
    """
    service = get_surreal_service()
    if not service.db:
        await service.connect()

    # Normalize judgment_id
    if not judgment_id.startswith("judgment:"):
        judgment_id = f"judgment:{judgment_id}"

    # Get documents for this case
    docs_result = await service.query(
        "SELECT * FROM document WHERE judgment_id = $judgment_id ORDER BY created_at DESC",
        {"judgment_id": judgment_id}
    )

    documents = []
    if docs_result and len(docs_result) > 0:
        first_item = docs_result[0]
        if isinstance(first_item, dict):
            if "result" in first_item:
                documents = first_item["result"] if isinstance(first_item["result"], list) else []
            elif "id" in first_item or "nom_fichier" in first_item:
                documents = docs_result
        elif isinstance(first_item, list):
            documents = first_item

    # Filter documents with texte_extrait
    docs_with_content = [
        doc for doc in documents
        if doc.get("texte_extrait") and len(doc.get("texte_extrait", "").strip()) > 0
    ]

    return docs_with_content


def _search_in_text(text: str, keywords: List[str], context_chars: int = 200) -> List[dict]:
    """
    Search for keywords in text and return matches with context.

    Args:
        text: Text to search in
        keywords: List of keywords to search for
        context_chars: Number of characters before/after match to include

    Returns:
        List of match dicts with 'keyword', 'context', 'position'
    """
    matches = []
    text_lower = text.lower()

    for keyword in keywords:
        keyword_lower = keyword.lower()
        # Find all occurrences
        start = 0
        while True:
            pos = text_lower.find(keyword_lower, start)
            if pos == -1:
                break

            # Extract context
            context_start = max(0, pos - context_chars)
            context_end = min(len(text), pos + len(keyword) + context_chars)
            context = text[context_start:context_end]

            # Add ellipsis if not at start/end
            if context_start > 0:
                context = "..." + context
            if context_end < len(text):
                context = context + "..."

            matches.append({
                "keyword": keyword,
                "context": context,
                "position": pos,
                "match_text": text[pos:pos + len(keyword)]
            })

            start = pos + len(keyword)

    return matches


@tool(name="search_documents")
async def search_documents(
    case_id: str,
    keywords: str,
    max_results: int = 10
) -> str:
    """
    Recherche par mots-clés EXACTS dans les documents d'un dossier.

    ⚠️ ATTENTION: Utilisez cet outil UNIQUEMENT si l'utilisateur demande explicitement de chercher un mot/phrase exact.
    Pour les questions normales, utilisez plutôt `semantic_search` qui comprend le sens de la question.

    Exemples de quand UTILISER cet outil:
    - L'utilisateur dit : "Cherche le mot exact 'signature'"
    - L'utilisateur dit : "Trouve toutes les occurrences de '1000$'"
    - L'utilisateur dit : "Recherche 'Jean Dupont' dans les documents"

    Exemples de quand NE PAS utiliser cet outil (utilisez `semantic_search` à la place):
    - "Qu'est-ce que le notariat ?" → utilisez semantic_search
    - "Quel est le prix ?" → utilisez semantic_search
    - "Résume ce document" → utilisez semantic_search

    Args:
        case_id: L'identifiant du dossier (ex: "1f9fc70e" ou "judgment:1f9fc70e")
        keywords: Mots-clés à rechercher, séparés par des virgules (ex: "contrat, signature, date")
        max_results: Nombre maximum de résultats à retourner par mot-clé (défaut: 10)

    Returns:
        Un résumé des résultats trouvés avec les passages pertinents
    """
    try:
        # Parse keywords
        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]

        if not keyword_list:
            return "Aucun mot-clé fourni. Veuillez spécifier au moins un mot-clé à rechercher."

        # Get case documents
        documents = await _get_case_documents(case_id)

        if not documents:
            return "Aucun document avec du contenu extractible trouvé dans ce dossier. Les documents doivent être transcrits ou avoir du texte extrait pour être recherchés."

        # Search in each document
        all_results = []
        total_matches = 0

        for doc in documents:
            doc_name = doc.get("nom_fichier", "Document sans nom")
            doc_id = doc.get("id", "")
            texte = doc.get("texte_extrait", "")

            if not texte:
                continue

            matches = _search_in_text(texte, keyword_list, context_chars=150)

            if matches:
                all_results.append({
                    "document": doc_name,
                    "document_id": doc_id,
                    "matches": matches[:max_results]  # Limit per document
                })
                total_matches += len(matches)

        if not all_results:
            keywords_str = ", ".join([f"'{k}'" for k in keyword_list])
            return f"Aucune occurrence trouvée pour les mots-clés {keywords_str} dans les {len(documents)} documents du dossier."

        # Format response
        keywords_str = ", ".join([f"**{k}**" for k in keyword_list])
        response = f"J'ai trouvé **{total_matches} occurrences** des mots-clés {keywords_str} dans **{len(all_results)} documents** :\n\n"

        for result in all_results:
            doc_name = result["document"]
            matches = result["matches"]

            response += f"### {doc_name}\n"
            response += f"*{len(matches)} occurrence(s) trouvée(s)*\n\n"

            # Group by keyword
            by_keyword = {}
            for match in matches:
                keyword = match["keyword"]
                if keyword not in by_keyword:
                    by_keyword[keyword] = []
                by_keyword[keyword].append(match)

            for keyword, keyword_matches in by_keyword.items():
                response += f"**Mot-clé: {keyword}** ({len(keyword_matches)} fois)\n"

                # Show first 3 matches for this keyword
                for i, match in enumerate(keyword_matches[:3], 1):
                    context = match["context"]
                    # Highlight the keyword in the context
                    context_highlighted = re.sub(
                        re.escape(keyword),
                        f"**{keyword}**",
                        context,
                        flags=re.IGNORECASE
                    )
                    response += f"  {i}. {context_highlighted}\n\n"

                if len(keyword_matches) > 3:
                    response += f"  *... et {len(keyword_matches) - 3} autres occurrences*\n\n"

            response += "\n"

        return response.strip()

    except Exception as e:
        logger.error(f"Document search error: {e}", exc_info=True)
        return f"Erreur lors de la recherche dans les documents: {str(e)}"


@tool(name="list_documents")
async def list_documents(case_id: str) -> str:
    """
    Liste tous les documents d'un dossier avec leur statut.

    Cet outil permet de voir tous les documents disponibles dans un dossier,
    leur type, et s'ils ont du contenu extractible (texte ou transcription).

    Args:
        case_id: L'identifiant du dossier (ex: "1f9fc70e" ou "judgment:1f9fc70e")

    Returns:
        Une liste formatée des documents avec leur statut
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize judgment_id
        judgment_id = case_id
        if not judgment_id.startswith("judgment:"):
            judgment_id = f"judgment:{judgment_id}"

        # Get documents for this case
        docs_result = await service.query(
            "SELECT * FROM document WHERE judgment_id = $judgment_id ORDER BY created_at DESC",
            {"judgment_id": judgment_id}
        )

        documents = []
        if docs_result and len(docs_result) > 0:
            first_item = docs_result[0]
            if isinstance(first_item, dict):
                if "result" in first_item:
                    documents = first_item["result"] if isinstance(first_item["result"], list) else []
                elif "id" in first_item or "nom_fichier" in first_item:
                    documents = docs_result
            elif isinstance(first_item, list):
                documents = first_item

        if not documents:
            return "Aucun document trouvé dans ce dossier."

        response = f"**{len(documents)} document(s) dans ce dossier:**\n\n"

        # Build a map of source relationships
        source_map = {}  # audio_filename -> transcription_filename
        pdf_extraction_map = {}  # pdf_filename -> markdown_filename

        # Map transcriptions to their audio sources
        for doc in documents:
            if doc.get("is_transcription") and doc.get("source_audio"):
                source_audio = doc.get("source_audio")
                source_map[source_audio] = doc.get("nom_fichier", "")

        # Map markdown files to their PDF sources (heuristic: same base name)
        md_files = [doc for doc in documents if doc.get("nom_fichier", "").lower().endswith(".md") and not doc.get("is_transcription")]
        pdf_files = [doc for doc in documents if doc.get("nom_fichier", "").lower().endswith(".pdf")]

        for md_doc in md_files:
            md_name = md_doc.get("nom_fichier", "")
            md_base = Path(md_name).stem  # Name without extension

            for pdf_doc in pdf_files:
                pdf_name = pdf_doc.get("nom_fichier", "")
                pdf_base = Path(pdf_name).stem

                if md_base == pdf_base:
                    pdf_extraction_map[pdf_name] = md_name
                    break

        # Categorize documents
        with_content = []
        without_content = []
        audio_files = []
        transcriptions = []
        pdf_extractions = []
        pdf_files = []

        AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac"}

        for doc in documents:
            doc_name = doc.get("nom_fichier", "Document sans nom")
            doc_type = doc.get("type_fichier", "").upper()
            doc_size = doc.get("taille", 0)
            texte_extrait = doc.get("texte_extrait", "")
            is_transcription = doc.get("is_transcription", False)
            source_audio = doc.get("source_audio", "")

            # Format size
            if doc_size < 1024:
                size_str = f"{doc_size} B"
            elif doc_size < 1024 * 1024:
                size_str = f"{doc_size / 1024:.1f} KB"
            else:
                size_str = f"{doc_size / (1024 * 1024):.1f} MB"

            # Check if audio
            ext = Path(doc_name).suffix.lower()
            is_audio = ext in AUDIO_EXTENSIONS
            is_pdf = ext == ".pdf"

            # Check if this markdown is a PDF extraction
            is_pdf_extraction = False
            source_pdf = ""
            if ext == ".md" and not is_transcription and texte_extrait:
                # Find matching PDF
                md_base = Path(doc_name).stem
                for pdf_name in pdf_extraction_map.keys():
                    if pdf_extraction_map[pdf_name] == doc_name:
                        is_pdf_extraction = True
                        source_pdf = pdf_name
                        break

            doc_info = {
                "name": doc_name,
                "type": doc_type,
                "size": size_str,
                "has_content": bool(texte_extrait),
                "is_transcription": is_transcription,
                "is_audio": is_audio,
                "is_pdf": is_pdf,
                "is_pdf_extraction": is_pdf_extraction,
                "word_count": len(texte_extrait.split()) if texte_extrait else 0,
                "source_audio": source_audio,
                "source_pdf": source_pdf,
                "transcription_file": source_map.get(doc_name, ""),
                "extraction_file": pdf_extraction_map.get(doc_name, "")
            }

            if is_transcription:
                transcriptions.append(doc_info)
            elif is_pdf_extraction:
                pdf_extractions.append(doc_info)
            elif is_pdf:
                pdf_files.append(doc_info)
            elif is_audio:
                audio_files.append(doc_info)
            elif texte_extrait:
                with_content.append(doc_info)
            else:
                without_content.append(doc_info)

        # Transcription files
        if transcriptions:
            response += "### 📝 Transcriptions audio (fichiers texte issus d'enregistrements audio):\n"
            response += "*IMPORTANT: Ces fichiers .md contiennent le texte extrait de fichiers audio. L'audio a DÉJÀ ÉTÉ transcrit.*\n\n"
            for doc in transcriptions:
                response += f"- **{doc['name']}** ({doc['type']}, {doc['size']}) - {doc['word_count']} mots\n"
                response += f"  📝 **Transcription complétée** du fichier audio **{doc['source_audio']}**\n"
                response += f"  ✅ Le fichier audio source a été traité et son contenu est maintenant disponible en texte\n\n"

        # PDF extractions
        if pdf_extractions:
            response += "### 📑 Extractions de documents PDF (fichiers texte issus de PDFs):\n"
            response += "*IMPORTANT: Ces fichiers .md contiennent le texte extrait de documents PDF. Le PDF a DÉJÀ ÉTÉ extrait.*\n\n"
            for doc in pdf_extractions:
                response += f"- **{doc['name']}** ({doc['type']}, {doc['size']}) - {doc['word_count']} mots\n"
                response += f"  📑 **Extraction complétée** du document PDF **{doc['source_pdf']}**\n"
                response += f"  ✅ Le document PDF source a été traité et son contenu est maintenant disponible en texte\n\n"

        # Documents with searchable content (excluding transcriptions and PDF extractions)
        if with_content:
            response += "### Autres documents avec contenu recherchable:\n"
            for doc in with_content:
                response += f"- **{doc['name']}** ({doc['type']}, {doc['size']})\n"
                response += f"  📄 Document texte - {doc['word_count']} mots\n\n"

        # Audio files
        if audio_files:
            response += "### 🎵 Fichiers audio originaux (enregistrements source):\n"
            for doc in audio_files:
                transcription_file = doc.get("transcription_file", "")
                if transcription_file:
                    response += f"- **{doc['name']}** ({doc['type']}, {doc['size']})\n"
                    response += f"  ✅ **STATUT: TRANSCRIPTION DÉJÀ EFFECTUÉE**\n"
                    response += f"  📄 Ce fichier audio a déjà été transcrit → voir le fichier texte **{transcription_file}**\n"
                    response += f"  ⚠️ **NE PAS re-transcrire** - La transcription existe déjà\n"
                    response += f"  💡 Pour analyser ce contenu, utilisez le fichier de transcription mentionné ci-dessus\n\n"
                else:
                    response += f"- **{doc['name']}** ({doc['type']}, {doc['size']})\n"
                    response += f"  ❌ **STATUT: PAS ENCORE TRANSCRIT**\n"
                    response += f"  ⏳ Ce fichier audio n'a pas de version texte\n"
                    response += f"  💡 Utilisez l'outil `transcribe_audio` pour créer une transcription\n\n"

        # PDF files
        if pdf_files:
            response += "### 📄 Documents PDF originaux (fichiers source):\n"
            for doc in pdf_files:
                extraction_file = doc.get("extraction_file", "")
                if extraction_file:
                    response += f"- **{doc['name']}** ({doc['type']}, {doc['size']})\n"
                    response += f"  ✅ **STATUT: EXTRACTION DÉJÀ EFFECTUÉE**\n"
                    response += f"  📄 Ce PDF a déjà été extrait → voir le fichier texte **{extraction_file}**\n"
                    response += f"  ⚠️ **NE PAS re-extraire** - L'extraction existe déjà\n"
                    response += f"  💡 Pour analyser ce contenu, utilisez le fichier d'extraction mentionné ci-dessus\n\n"
                else:
                    response += f"- **{doc['name']}** ({doc['type']}, {doc['size']})\n"
                    response += f"  ❌ **STATUT: CONTENU NON EXTRACTIBLE**\n"
                    response += f"  ℹ️ PDF scanné ou image - nécessite OCR\n\n"

        # Documents without content (excluding PDFs)
        if without_content:
            response += "### Autres documents:\n"
            for doc in without_content:
                response += f"- **{doc['name']}** ({doc['type']}, {doc['size']})\n"
                response += f"  ℹ️ Contenu non extractible (image, document scanné, etc.)\n\n"

        # Summary
        searchable_count = len(transcriptions) + len(pdf_extractions) + len(with_content)
        response += f"\n**Résumé:** {searchable_count} document(s) avec contenu recherchable"

        return response.strip()

    except Exception as e:
        logger.error(f"List documents error: {e}", exc_info=True)
        return f"Erreur lors de la récupération de la liste des documents: {str(e)}"
