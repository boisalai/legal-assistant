#!/bin/bash
# Script pour diagnostiquer et corriger les tests qui échouent
# Usage: ./scripts/fix_tests.sh

set -e

echo "======================================"
echo "🔧 Diagnostic et Correction des Tests"
echo "======================================"
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

cd "$(dirname "$0")/../backend"

echo "📍 Répertoire: $(pwd)"
echo ""

# Fonction pour exécuter un test et capturer le résultat
run_test() {
    local test_path=$1
    local test_name=$(basename "$test_path")

    echo -e "${YELLOW}▶ Test: $test_name${NC}"

    if uv run pytest "$test_path" -v --tb=short 2>&1 | tee /tmp/test_output.log; then
        echo -e "${GREEN}✅ PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        echo "Voir détails dans /tmp/test_output.log"
        return 1
    fi
}

echo "======================================"
echo "1️⃣  Tests CRITIQUES (Documents)"
echo "======================================"
echo ""

# Tests critiques à corriger en priorité
CRITICAL_TESTS=(
    "tests/test_documents.py::TestDocumentsCRUD::test_upload_document"
    "tests/test_documents.py::TestDocumentsCRUD::test_get_document"
    "tests/test_documents.py::TestDocumentWorkflow::test_full_document_lifecycle"
)

passed=0
failed=0

for test in "${CRITICAL_TESTS[@]}"; do
    if run_test "$test"; then
        ((passed++))
    else
        ((failed++))
    fi
    echo ""
done

echo "======================================"
echo "2️⃣  Tests CAIJ"
echo "======================================"
echo ""

CAIJ_TESTS=(
    "tests/test_caij_service.py::test_caij_multiple_searches"
    "tests/test_caij_service.py::test_caij_tool_integration"
    "tests/test_caij_service.py::test_caij_invalid_query"
)

for test in "${CAIJ_TESTS[@]}"; do
    if run_test "$test"; then
        ((passed++))
    else
        ((failed++))
    fi
    echo ""
done

echo "======================================"
echo "3️⃣  Tests Courses"
echo "======================================"
echo ""

if run_test "tests/test_courses.py::TestCoursesCRUD::test_create_course_minimal"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

echo "======================================"
echo "4️⃣  Tests Linked Directories"
echo "======================================"
echo ""

if run_test "tests/test_linked_directories.py::TestLinkSingleFile::test_link_single_file"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

echo "======================================"
echo "📊 Résumé"
echo "======================================"
echo -e "${GREEN}✅ Passés: $passed${NC}"
echo -e "${RED}❌ Échoués: $failed${NC}"
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}🎉 Tous les tests critiques passent!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Des tests échouent encore. Voir logs ci-dessus.${NC}"
    echo ""
    echo "💡 Prochaines étapes:"
    echo "  1. Examiner les logs dans /tmp/test_output.log"
    echo "  2. Exécuter un test spécifique en mode debug:"
    echo "     uv run pytest <test_path> -vvs"
    echo "  3. Ajouter des breakpoints si nécessaire"
    echo ""
    exit 1
fi
