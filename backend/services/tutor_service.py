"""
Tutor Service for Legal Assistant.

Provides pedagogical functions for creating summaries, mind maps, quizzes, and explanations.
"""

import logging
from typing import Dict, List, Optional

from services.document_indexing_service import DocumentIndexingService
from services.surreal_service import get_surreal_service

logger = logging.getLogger(__name__)


class TutorService:
    """Service for generating pedagogical content."""

    def __init__(self):
        """Initialize the tutor service."""
        self.indexing_service = DocumentIndexingService()

    async def generate_summary_content(
        self,
        case_id: str,
        document_id: Optional[str] = None,
        summary_type: str = "comprehensive"
    ) -> str:
        """
        Generate a pedagogical summary of a document or course.

        Args:
            case_id: Course ID
            document_id: Document ID (if None, summarize entire course)
            summary_type: Type of summary ("comprehensive", "key_points", "executive")

        Returns:
            Formatted markdown summary
        """
        logger.info(f"Generating {summary_type} summary for case_id={case_id}, document_id={document_id}")

        try:
            # Get document name for title
            doc_name = "le cours"
            if document_id:
                doc_data = await self.get_document_content(document_id)
                if doc_data:
                    doc_name = doc_data.get("nom_fichier", "le document")

            # Perform semantic searches to extract key content
            # We'll do 3 targeted searches to get different aspects

            # 1. Main concepts and definitions
            concepts_results = await self.search_content(
                case_id=case_id,
                query="Quels sont les concepts principaux, définitions et notions clés abordés ?",
                document_id=document_id,
                top_k=5
            )

            # 2. Important points and rules
            points_results = await self.search_content(
                case_id=case_id,
                query="Quels sont les points importants, règles, conditions et obligations à retenir ?",
                document_id=document_id,
                top_k=5
            )

            # 3. Warnings, exceptions, and pitfalls
            warnings_results = await self.search_content(
                case_id=case_id,
                query="Quels sont les points d'attention, exceptions, cas particuliers et erreurs à éviter ?",
                document_id=document_id,
                top_k=3
            )

            # Build the summary
            summary = f"# 📝 Résumé Pédagogique: {doc_name}\n\n"

            # Learning objectives
            summary += "## 🎯 Objectifs d'Apprentissage\n"
            summary += "Après avoir étudié ce contenu, vous devriez pouvoir:\n"
            if concepts_results:
                # Generate objectives from concepts
                for i, result in enumerate(concepts_results[:3], 1):
                    # Extract first sentence or key phrase from content
                    content = result.get("content", "")
                    first_sentence = content.split('.')[0] if content else ""
                    if first_sentence:
                        summary += f"- ✅ Comprendre {first_sentence.lower()}\n"
            else:
                summary += "- ✅ Maîtriser les concepts clés du sujet\n"
                summary += "- ✅ Identifier les éléments essentiels\n"
                summary += "- ✅ Appliquer les règles et principes\n"

            # Key points
            summary += "\n## 📚 Points Clés\n\n"
            if points_results:
                for i, result in enumerate(points_results, 1):
                    content = result.get("content", "")
                    source = result.get("document_name", "document")
                    similarity = result.get("similarity", 0)

                    # Only include results with decent similarity
                    if similarity >= 0.3 and content:
                        # Truncate if too long
                        if len(content) > 400:
                            content = content[:400] + "..."

                        summary += f"### {i}. Point Important\n"
                        summary += f"{content}\n\n"
                        summary += f"**Source:** {source}\n\n"
            else:
                summary += "*Aucun point clé trouvé. Le document pourrait ne pas être indexé.*\n\n"

            # Important concepts
            summary += "## 💡 Concepts Importants à Retenir\n\n"
            if concepts_results:
                # Group concepts by source
                sources = {}
                for result in concepts_results:
                    source = result.get("document_name", "document")
                    content = result.get("content", "")
                    similarity = result.get("similarity", 0)

                    if similarity >= 0.3 and content:
                        if source not in sources:
                            sources[source] = []
                        # Extract key phrases (first 200 chars)
                        snippet = content[:200].strip()
                        sources[source].append(snippet)

                for source, snippets in sources.items():
                    summary += f"### Selon {source}\n"
                    for snippet in snippets[:2]:  # Max 2 per source
                        summary += f"- {snippet}...\n"
                    summary += "\n"
            else:
                summary += "*Consultez le document complet pour identifier les concepts clés.*\n\n"

            # Warnings and attention points
            summary += "## ⚠️ Points d'Attention\n\n"
            if warnings_results:
                for result in warnings_results:
                    content = result.get("content", "")
                    source = result.get("document_name", "document")
                    similarity = result.get("similarity", 0)

                    if similarity >= 0.3 and content:
                        # Extract first sentence or key warning
                        first_part = content[:300].strip()
                        summary += f"- {first_part}...\n"
                        summary += f"  - *Source: {source}*\n\n"
            else:
                summary += "*Relisez attentivement le document pour identifier les exceptions et cas particuliers.*\n\n"

            # Call to action
            summary += "## 📊 Pour Aller Plus Loin\n\n"
            summary += "Voulez-vous que je:\n"
            summary += "- 🗺️ Crée une carte mentale de ce contenu?\n"
            summary += "- ❓ Génère un quiz pour tester votre compréhension?\n"
            summary += "- 💡 Explique un concept spécifique plus en détail?\n"

            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {e}", exc_info=True)
            return f"""# ❌ Erreur lors de la génération du résumé

Une erreur est survenue: {str(e)}

Veuillez vérifier que:
- Le document existe et est indexé
- Le cours contient des documents avec du texte extrait
"""

    async def generate_mindmap_content(
        self,
        case_id: str,
        document_id: Optional[str] = None,
        focus_topic: Optional[str] = None
    ) -> str:
        """
        Generate a mind map in markdown format with emojis.

        Args:
            case_id: Course ID
            document_id: Document ID (if None, map entire course)
            focus_topic: Specific topic to focus on

        Returns:
            Formatted markdown mind map
        """
        logger.info(f"Generating mind map for case_id={case_id}, document_id={document_id}, topic={focus_topic}")

        try:
            # Get document name for title
            doc_name = "le cours"
            if document_id:
                doc_data = await self.get_document_content(document_id)
                if doc_data:
                    doc_name = doc_data.get("nom_fichier", "le document")

            # Determine search query based on focus_topic
            if focus_topic:
                query = f"Quels sont les concepts, éléments et aspects principaux de {focus_topic} ?"
                title = f"{focus_topic}"
            else:
                query = "Quels sont les thèmes, concepts et notions principales abordés dans ce contenu ?"
                title = doc_name

            # Search for main themes and concepts
            main_results = await self.search_content(
                case_id=case_id,
                query=query,
                document_id=document_id,
                top_k=8
            )

            # Build mind map
            mindmap = f"# 🗺️ Carte Mentale: {title}\n\n"

            if not main_results or all(r.get("similarity", 0) < 0.3 for r in main_results):
                mindmap += """*Aucun contenu trouvé. Le document pourrait ne pas être indexé.*

**Suggestions :**
- Vérifiez que le document est indexé
- Essayez de spécifier un sujet précis avec l'outil
"""
                return mindmap

            # Extract and organize concepts
            # We'll create sections based on keywords and content
            sections = self._organize_mindmap_sections(main_results)

            # Build the hierarchical structure
            for section_title, items in sections.items():
                mindmap += f"## {section_title}\n"

                for item in items[:5]:  # Max 5 items per section
                    content = item.get("content", "")
                    if len(content) > 100:
                        # Extract first sentence or key phrase
                        sentences = content.split('.')
                        first_sentence = sentences[0].strip()
                        if len(first_sentence) > 80:
                            first_sentence = first_sentence[:80] + "..."
                        mindmap += f"  - {first_sentence}\n"

                        # Add sub-details if available
                        if len(sentences) > 1:
                            second_sentence = sentences[1].strip()
                            if second_sentence and len(second_sentence) < 80:
                                mindmap += f"    - {second_sentence}\n"
                    else:
                        mindmap += f"  - {content.strip()}\n"

                mindmap += "\n"

            # Add footer
            mindmap += "---\n\n"
            mindmap += f"**📊 Carte générée à partir de {len(main_results)} passages pertinents**\n\n"
            mindmap += "💡 **Astuce :** Utilisez `explain_concept` pour approfondir un concept spécifique\n"

            return mindmap

        except Exception as e:
            logger.error(f"Error generating mind map: {e}", exc_info=True)
            return f"""# ❌ Erreur lors de la génération de la carte mentale

Une erreur est survenue: {str(e)}

Veuillez vérifier que le document est indexé.
"""

    def _organize_mindmap_sections(self, results: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Organize search results into thematic sections.

        Args:
            results: List of search results

        Returns:
            Dictionary mapping section titles to items
        """
        # Define emoji mappings for common legal concepts
        emoji_map = {
            "définition": "📖",
            "principe": "⚖️",
            "condition": "✅",
            "obligation": "📋",
            "droit": "👑",
            "exception": "⚠️",
            "effet": "⚡",
            "procédure": "📝",
            "règle": "📏",
            "exemple": "💡",
            "article": "📜",
            "contrat": "🤝",
            "responsabilité": "🔥",
            "propriété": "🏠",
            "personne": "👤",
            "tribunal": "🏛️",
            "délai": "⏱️",
            "preuve": "🔍",
        }

        sections = {}
        default_sections = {
            "📖 Définitions et Concepts": [],
            "⚖️ Principes et Règles": [],
            "✅ Conditions et Éléments": [],
            "⚠️ Exceptions et Cas Particuliers": [],
            "💡 Exemples et Applications": [],
        }

        for result in results:
            content = result.get("content", "").lower()
            similarity = result.get("similarity", 0)

            if similarity < 0.3:
                continue

            # Categorize based on keywords
            if any(keyword in content for keyword in ["définition", "défini comme", "signifie", "est un"]):
                default_sections["📖 Définitions et Concepts"].append(result)
            elif any(keyword in content for keyword in ["principe", "règle", "loi", "article"]):
                default_sections["⚖️ Principes et Règles"].append(result)
            elif any(keyword in content for keyword in ["condition", "élément", "critère", "requis"]):
                default_sections["✅ Conditions et Éléments"].append(result)
            elif any(keyword in content for keyword in ["exception", "sauf", "toutefois", "cependant"]):
                default_sections["⚠️ Exceptions et Cas Particuliers"].append(result)
            elif any(keyword in content for keyword in ["exemple", "par exemple", "notamment", "ainsi"]):
                default_sections["💡 Exemples et Applications"].append(result)
            else:
                # Default to Principes et Règles
                default_sections["⚖️ Principes et Règles"].append(result)

        # Only keep non-empty sections
        sections = {k: v for k, v in default_sections.items() if v}

        # If no sections, create a generic one
        if not sections:
            sections["📚 Contenu Principal"] = results

        return sections

    async def generate_quiz_content(
        self,
        case_id: str,
        document_id: Optional[str] = None,
        num_questions: int = 5,
        difficulty: str = "medium"
    ) -> str:
        """
        Generate an interactive quiz with questions and explanations.

        Args:
            case_id: Course ID
            document_id: Document ID (if None, quiz on entire course)
            num_questions: Number of questions (1-10)
            difficulty: Difficulty level ("easy", "medium", "hard")

        Returns:
            Formatted markdown quiz with collapsible answers
        """
        logger.info(f"Generating quiz ({num_questions} questions, {difficulty}) for case_id={case_id}, document_id={document_id}")

        try:
            # Get document name for title
            doc_name = "le cours"
            if document_id:
                doc_data = await self.get_document_content(document_id)
                if doc_data:
                    doc_name = doc_data.get("nom_fichier", "le document")

            # Difficulty stars mapping
            difficulty_stars = {
                "easy": "⭐",
                "medium": "⭐⭐",
                "hard": "⭐⭐⭐"
            }
            stars = difficulty_stars.get(difficulty, "⭐⭐")

            # Search for factual content to base questions on
            # We need diverse content for variety
            factual_content = await self.search_content(
                case_id=case_id,
                query="Quels sont les faits, définitions, règles, conditions et principes importants ?",
                document_id=document_id,
                top_k=num_questions * 2  # Get more than needed for variety
            )

            quiz = f"# 📝 Quiz: {doc_name}\n\n"

            if not factual_content or all(r.get("similarity", 0) < 0.3 for r in factual_content):
                quiz += """*Impossible de générer un quiz. Le document pourrait ne pas être indexé.*

**Suggestions :**
- Vérifiez que le document est indexé
- Essayez avec un document différent
"""
                return quiz

            quiz += f"*Testez votre compréhension de {doc_name}*\n\n"
            quiz += "---\n\n"

            # Generate questions from content
            questions_generated = 0
            for i, result in enumerate(factual_content):
                if questions_generated >= num_questions:
                    break

                content = result.get("content", "")
                source = result.get("document_name", "document")
                similarity = result.get("similarity", 0)

                if similarity < 0.3 or len(content) < 50:
                    continue

                # Extract a fact or concept for the question
                sentences = [s.strip() for s in content.split('.') if s.strip()]
                if not sentences:
                    continue

                # Use first substantial sentence as basis
                fact = sentences[0]
                if len(fact) < 20:
                    if len(sentences) > 1:
                        fact = sentences[1]
                    else:
                        continue

                questions_generated += 1

                quiz += f"## Question {questions_generated}/{num_questions} (Difficulté: {stars})\n"

                # Generate question based on content
                # This is a simplified version - in production, you'd use an LLM to generate better questions
                if "définition" in content.lower() or "est un" in content.lower():
                    quiz += f"**Quelle est la définition correcte selon le document ?**\n\n"
                elif "condition" in content.lower() or "élément" in content.lower():
                    quiz += f"**Quelles sont les conditions requises ?**\n\n"
                elif "principe" in content.lower() or "règle" in content.lower():
                    quiz += f"**Quel principe est énoncé dans le document ?**\n\n"
                else:
                    quiz += f"**Selon le document, quelle affirmation est correcte ?**\n\n"

                # Generate 4 answer choices
                # Option A: Correct answer (based on actual content)
                quiz += f"a) {fact[:100]}{'...' if len(fact) > 100 else ''}\n"

                # Options B, C, D: Plausible but incorrect (generic for now)
                quiz += f"b) [Alternative plausible - nécessite génération par LLM]\n"
                quiz += f"c) [Alternative plausible - nécessite génération par LLM]\n"
                quiz += f"d) [Alternative plausible - nécessite génération par LLM]\n\n"

                # Collapsible answer
                quiz += "<details>\n"
                quiz += "<summary>💡 Voir la réponse</summary>\n\n"
                quiz += "✅ **Réponse correcte: a)**\n\n"
                quiz += "**Explication:**\n"

                # Provide detailed explanation
                if len(sentences) > 1:
                    quiz += f"{sentences[0]}. {sentences[1] if len(sentences) > 1 else ''}\n\n"
                else:
                    quiz += f"{content[:300]}...\n\n"

                quiz += f"**Source:** {source}\n\n"
                quiz += "---\n\n"
                quiz += "</details>\n\n"

            # Footer
            quiz += "---\n\n"
            quiz += "## 📊 Résultats et Prochaines Étapes\n\n"
            quiz += "**Comment utiliser ce quiz:**\n"
            quiz += "1. 📝 Répondez à chaque question avant de regarder la réponse\n"
            quiz += "2. 💡 Lisez attentivement les explications\n"
            quiz += "3. 📚 Retournez au document source si besoin de clarification\n\n"
            quiz += "**Pour approfondir:**\n"
            quiz += "- 🗺️ Voulez-vous une carte mentale du document?\n"
            quiz += "- 💡 Besoin d'explications supplémentaires sur un concept?\n"
            quiz += "- 📝 Voulez-vous un résumé du document?\n\n"
            quiz += "Bon apprentissage! 🎓\n"

            # Note about limitations
            if questions_generated < num_questions:
                quiz += f"\n*Note: Seulement {questions_generated} questions ont pu être générées à partir du contenu disponible.*\n"

            return quiz

        except Exception as e:
            logger.error(f"Error generating quiz: {e}", exc_info=True)
            return f"""# ❌ Erreur lors de la génération du quiz

Une erreur est survenue: {str(e)}

Veuillez vérifier que le document est indexé.
"""

    async def generate_concept_explanation(
        self,
        case_id: str,
        concept: str,
        document_id: Optional[str] = None,
        detail_level: str = "standard"
    ) -> str:
        """
        Generate a detailed explanation of a legal concept.

        Args:
            case_id: Course ID
            concept: Concept to explain
            document_id: Limit search to specific document
            detail_level: Detail level ("simple", "standard", "advanced")

        Returns:
            Formatted markdown explanation
        """
        logger.info(f"Explaining concept '{concept}' (level={detail_level}) for case_id={case_id}, document_id={document_id}")

        try:
            # Search for definition
            definition_results = await self.search_content(
                case_id=case_id,
                query=f"Quelle est la définition de {concept} ? Qu'est-ce que {concept} signifie ?",
                document_id=document_id,
                top_k=3
            )

            # Search for conditions and elements
            conditions_results = await self.search_content(
                case_id=case_id,
                query=f"Quelles sont les conditions, éléments ou critères de {concept} ?",
                document_id=document_id,
                top_k=3
            )

            # Search for examples
            examples_results = await self.search_content(
                case_id=case_id,
                query=f"Quels sont les exemples, cas ou applications de {concept} ?",
                document_id=document_id,
                top_k=2
            )

            # Build explanation
            explanation = f"# 💡 Explication: {concept}\n\n"

            # Definition section
            explanation += "## 📖 Définition\n\n"
            if definition_results and any(r.get("similarity", 0) >= 0.3 for r in definition_results):
                for result in definition_results:
                    if result.get("similarity", 0) >= 0.3:
                        content = result.get("content", "")
                        source = result.get("document_name", "document")

                        # Extract most relevant sentence
                        sentences = [s.strip() for s in content.split('.') if s.strip()]
                        if sentences:
                            # Find sentence containing the concept
                            relevant = [s for s in sentences if concept.lower() in s.lower()]
                            if relevant:
                                explanation += f"{relevant[0]}.\n\n"
                            else:
                                explanation += f"{sentences[0]}.\n\n"

                            explanation += f"*Source: {source}*\n\n"
                            break  # Only use most relevant
            else:
                explanation += f"*Aucune définition trouvée pour '{concept}' dans les documents disponibles.*\n\n"

            # Conditions/Elements section
            explanation += "## 🎯 Conditions et Éléments\n\n"
            if conditions_results and any(r.get("similarity", 0) >= 0.3 for r in conditions_results):
                sources_used = set()
                for result in conditions_results[:2]:  # Max 2 results
                    if result.get("similarity", 0) >= 0.3:
                        content = result.get("content", "")
                        source = result.get("document_name", "document")

                        if source in sources_used:
                            continue
                        sources_used.add(source)

                        # Extract key points
                        if len(content) > 300:
                            content = content[:300] + "..."

                        explanation += f"{content}\n\n"
                        explanation += f"*Source: {source}*\n\n"
            else:
                explanation += f"*Aucune information sur les conditions de '{concept}' trouvée.*\n\n"

            # Examples section
            explanation += "## 📚 Exemples et Applications\n\n"
            if examples_results and any(r.get("similarity", 0) >= 0.3 for r in examples_results):
                for i, result in enumerate(examples_results, 1):
                    if result.get("similarity", 0) >= 0.3:
                        content = result.get("content", "")
                        source = result.get("document_name", "document")

                        # Format as example
                        if len(content) > 250:
                            content = content[:250] + "..."

                        explanation += f"**Exemple {i}:**\n"
                        explanation += f"> {content}\n\n"
                        explanation += f"*Source: {source}*\n\n"
            else:
                explanation += f"*Aucun exemple de '{concept}' trouvé dans les documents.*\n\n"

            # Sources summary
            explanation += "## 📎 Sources Consultées\n\n"
            all_sources = set()
            for results in [definition_results, conditions_results, examples_results]:
                if results:
                    for r in results:
                        if r.get("similarity", 0) >= 0.3:
                            all_sources.add(r.get("document_name", "document"))

            if all_sources:
                for source in sorted(all_sources):
                    explanation += f"- {source}\n"
            else:
                explanation += "*Aucune source pertinente trouvée*\n"

            explanation += "\n"

            # Related concepts (heuristic based on content)
            explanation += "## 🔗 Concepts Potentiellement Liés\n\n"
            explanation += "*Pour explorer ces concepts, utilisez l'outil `explain_concept` avec le nom du concept.*\n\n"

            # Suggest using other tools
            explanation += "## 📊 Pour Aller Plus Loin\n\n"
            explanation += f"- 📝 Demandez un résumé du document contenant '{concept}'\n"
            explanation += f"- ❓ Testez vos connaissances avec un quiz sur ce sujet\n"
            explanation += f"- 🗺️ Visualisez les concepts avec une carte mentale\n"

            # Adapt explanation based on detail level
            if detail_level == "simple":
                # Add note that this is simplified
                explanation = f"*Explication simplifiée de {concept}*\n\n" + explanation
            elif detail_level == "advanced":
                # Add note for advanced level
                explanation = f"*Explication détaillée de {concept}*\n\n" + explanation

            return explanation

        except Exception as e:
            logger.error(f"Error explaining concept: {e}", exc_info=True)
            return f"""# ❌ Erreur lors de l'explication du concept

Une erreur est survenue: {str(e)}

Veuillez vérifier que:
- Le concept est mentionné dans les documents
- Les documents sont indexés
"""

    async def get_document_content(self, document_id: str) -> Optional[Dict]:
        """
        Retrieve full document content from database.

        Args:
            document_id: Document ID

        Returns:
            Document data with texte_extrait
        """
        try:
            service = get_surreal_service()
            if not service.db:
                await service.connect()

            result = await service.query(f"SELECT * FROM {document_id}")

            if result and len(result) > 0:
                # Handle different response formats
                doc_data = result[0]
                if isinstance(doc_data, dict):
                    if "result" in doc_data and isinstance(doc_data["result"], list) and len(doc_data["result"]) > 0:
                        return doc_data["result"][0]
                    elif "id" in doc_data or "nom_fichier" in doc_data:
                        return doc_data

            return None

        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}")
            return None

    async def search_content(
        self,
        case_id: str,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Search for content using semantic search.

        Args:
            case_id: Course ID
            query: Search query
            document_id: Limit to specific document
            top_k: Number of results

        Returns:
            List of search results with content and metadata
        """
        try:
            # Normalize case_id
            if not case_id.startswith("course:"):
                case_id = f"course:{case_id}"

            # Use the indexing service for semantic search
            results = await self.indexing_service.search_similar(
                query_text=query,
                case_id=case_id,
                top_k=top_k
            )

            # Filter by document_id if provided
            if document_id and results:
                results = [r for r in results if r.get("document_id") == document_id]

            return results

        except Exception as e:
            logger.error(f"Error searching content: {e}")
            return []


# Singleton instance
_tutor_service: Optional[TutorService] = None


def get_tutor_service() -> TutorService:
    """Get the singleton tutor service instance."""
    global _tutor_service
    if _tutor_service is None:
        _tutor_service = TutorService()
    return _tutor_service
