"""
Tests for the multi-agent legal research team.

Tests the Chercheur + Validateur 2-agent prototype.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from tools.validation_tool import (
    _extract_citations_from_text,
    _verify_article_ccq,
)
from agents.legal_research_team import (
    is_legal_research_query,
)


# ============================================================================
# Tests for citation extraction
# ============================================================================

class TestCitationExtraction:
    """Tests for _extract_citations_from_text."""

    def test_extract_ccq_articles(self):
        """Test extraction of Code civil du Québec articles."""
        text = "L'article 1726 C.c.Q. prévoit les vices cachés. Voir aussi art. 1728 C.c.Q."
        citations = _extract_citations_from_text(text)

        assert len(citations["articles"]) == 2
        assert "art. 1726 C.c.Q." in citations["articles"]
        assert "art. 1728 C.c.Q." in citations["articles"]

    def test_extract_ccq_full_name(self):
        """Test extraction with 'Code civil du Québec' spelled out."""
        text = "L'article 427 du Code civil du Québec concerne la tutelle."
        citations = _extract_citations_from_text(text)

        assert len(citations["articles"]) == 1
        assert "art. 427 C.c.Q." in citations["articles"]

    def test_extract_jurisprudence(self):
        """Test extraction of jurisprudence citations."""
        text = "Selon Tremblay c. Gagnon, 2024 QCCS, le tribunal a statué..."
        citations = _extract_citations_from_text(text)

        assert len(citations["jurisprudence"]) >= 1
        # Check that at least "Tremblay c. Gagnon" is extracted
        assert any("Tremblay c. Gagnon" in j for j in citations["jurisprudence"])

    def test_extract_lrq(self):
        """Test extraction of laws (L.R.Q.)."""
        text = "La Loi sur la protection du consommateur (L.R.Q., c. P-40.1) s'applique."
        citations = _extract_citations_from_text(text)

        assert len(citations["lois"]) == 1
        assert "L.R.Q., c. P-40.1" in citations["lois"]

    def test_no_citations(self):
        """Test with text containing no citations."""
        text = "Bonjour, comment allez-vous aujourd'hui?"
        citations = _extract_citations_from_text(text)

        assert len(citations["articles"]) == 0
        assert len(citations["jurisprudence"]) == 0
        assert len(citations["lois"]) == 0


# ============================================================================
# Tests for article validation
# ============================================================================

class TestArticleValidation:
    """Tests for _verify_article_ccq."""

    @pytest.mark.asyncio
    async def test_valid_article(self):
        """Test validation of a valid C.c.Q. article."""
        result = await _verify_article_ccq("1726")

        assert result["valid"] is True
        assert "Code civil du Québec" in result["source"]

    @pytest.mark.asyncio
    async def test_invalid_article_too_high(self):
        """Test detection of article number outside valid range."""
        result = await _verify_article_ccq("9999")

        assert result["valid"] is False
        assert "hors plage" in result["note"]

    @pytest.mark.asyncio
    async def test_valid_article_edge_case(self):
        """Test edge case: article 1 and article 3168."""
        result_first = await _verify_article_ccq("1")
        result_last = await _verify_article_ccq("3168")

        assert result_first["valid"] is True
        assert result_last["valid"] is True

    @pytest.mark.asyncio
    async def test_decimal_article(self):
        """Test article with decimal (e.g., 1726.1)."""
        result = await _verify_article_ccq("1726.1")

        assert result["valid"] is True  # 1726 is in valid range


# ============================================================================
# Tests for is_legal_research_query
# ============================================================================

class TestLegalQueryDetection:
    """Tests for is_legal_research_query."""

    def test_detect_article_query(self):
        """Test detection of query about a specific article."""
        query = "Qu'est-ce que l'article 1726 du Code civil prévoit?"
        assert is_legal_research_query(query) is True

    def test_detect_vices_caches_query(self):
        """Test detection of query about vices cachés."""
        query = "Quels sont les recours pour vices cachés?"
        assert is_legal_research_query(query) is True

    def test_detect_jurisprudence_query(self):
        """Test detection of query about jurisprudence."""
        query = "Y a-t-il de la jurisprudence récente sur les servitudes?"
        assert is_legal_research_query(query) is True

    def test_simple_greeting_not_legal(self):
        """Test that simple greetings are not detected as legal queries."""
        query = "Bonjour, comment vas-tu?"
        assert is_legal_research_query(query) is False

    def test_technical_question_not_legal(self):
        """Test that technical questions are not detected as legal queries."""
        query = "Comment installer Python sur mon ordinateur?"
        assert is_legal_research_query(query) is False


# ============================================================================
# Tests for verify_legal_citations (using internal implementation)
# ============================================================================

class TestVerifyLegalCitations:
    """Tests for citation verification logic."""

    @pytest.mark.asyncio
    async def test_verify_valid_article_via_extraction(self):
        """Test verification of a text with valid articles using extraction."""
        text = "L'article 1726 C.c.Q. prévoit les recours pour vices cachés."

        citations = _extract_citations_from_text(text)
        assert "art. 1726 C.c.Q." in citations["articles"]

        # Verify the article is valid
        result = await _verify_article_ccq("1726")
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_verify_invalid_article_via_extraction(self):
        """Test detection of invalid article number using extraction."""
        text = "L'article 9999 C.c.Q. n'existe pas."

        citations = _extract_citations_from_text(text)
        assert "art. 9999 C.c.Q." in citations["articles"]

        # Verify the article is invalid
        result = await _verify_article_ccq("9999")
        assert result["valid"] is False
        assert "hors plage" in result["note"]

    def test_no_citations_in_text(self):
        """Test extraction of text without citations."""
        text = "Bonjour, ceci est un texte sans référence juridique."

        citations = _extract_citations_from_text(text)

        assert len(citations["articles"]) == 0
        assert len(citations["jurisprudence"]) == 0
        assert len(citations["lois"]) == 0


# ============================================================================
# Tests for citation extraction with mixed types
# ============================================================================

class TestMixedCitationExtraction:
    """Tests for extraction of mixed citation types."""

    def test_extract_mixed_citations(self):
        """Test extraction of mixed citation types."""
        text = """
        L'article 1726 C.c.Q. établit les principes.
        Selon Tremblay c. Gagnon, 2024 QCCS, le tribunal a confirmé.
        La L.R.Q., c. P-40.1 s'applique également.
        """

        citations = _extract_citations_from_text(text)

        assert len(citations["articles"]) >= 1
        assert "art. 1726 C.c.Q." in citations["articles"]
        assert len(citations["jurisprudence"]) >= 1
        assert len(citations["lois"]) >= 1


# ============================================================================
# Tests for create_legal_research_team
# ============================================================================

class TestLegalResearchTeam:
    """Tests for create_legal_research_team."""

    @pytest.mark.skip(reason="Requires actual Agno model instance, not MagicMock")
    def test_team_creation(self):
        """Test that team is created with correct structure."""
        # This test requires a real model instance to work with Agno
        # It's tested manually during integration testing
        pass

    @pytest.mark.skip(reason="Requires actual Agno model instance, not MagicMock")
    def test_team_has_correct_tools(self):
        """Test that agents have the correct tools assigned."""
        # This test requires a real model instance to work with Agno
        pass

    @pytest.mark.skip(reason="Requires actual Agno model instance, not MagicMock")
    def test_case_id_injected_in_instructions(self):
        """Test that case_id is properly injected into agent instructions."""
        # This test requires a real model instance to work with Agno
        pass


# ============================================================================
# Integration test (mocked)
# ============================================================================

class TestMultiAgentIntegration:
    """Integration tests for the multi-agent flow."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires model server running")
    async def test_team_responds_to_legal_query(self):
        """Test that team can process a legal query end-to-end."""
        # This test would require a running model server
        # Skipped by default, but can be run manually for integration testing
        pass
