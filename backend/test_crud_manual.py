"""
Script de test manuel pour les opérations CRUD des cours.
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/courses"

def test_create_course():
    """Test de création d'un cours."""
    print("\n🧪 Test 1: Création d'un cours")
    print("=" * 50)

    data = {
        "title": "Test - Introduction au droit",
        "description": "Cours de test automatisé",
        "course_code": "TEST-001",
        "professor": "Prof. Test",
        "credits": 3,
        "color": "#FF5733"
    }

    response = requests.post(BASE_URL, json=data)
    print(f"Status: {response.status_code}")

    if response.status_code == 201:
        course = response.json()
        print("✅ Cours créé avec succès!")
        print(f"ID: {course['id']}")
        print(f"Titre: {course['title']}")
        return course['id']
    else:
        print(f"❌ Échec: {response.text}")
        return None


def test_get_course(course_id):
    """Test de récupération d'un cours."""
    print(f"\n🧪 Test 2: Récupération du cours {course_id}")
    print("=" * 50)

    response = requests.get(f"{BASE_URL}/{course_id}")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        course = response.json()
        print("✅ Cours récupéré avec succès!")
        print(f"Titre: {course['title']}")
        print(f"Professeur: {course['professor']}")
        print(f"Crédits: {course['credits']}")
    else:
        print(f"❌ Échec: {response.text}")


def test_update_course(course_id):
    """Test de mise à jour d'un cours."""
    print(f"\n🧪 Test 3: Mise à jour du cours {course_id}")
    print("=" * 50)

    update_data = {
        "title": "Test - Cours mis à jour",
        "professor": "Prof. Updated",
        "credits": 4
    }

    response = requests.put(f"{BASE_URL}/{course_id}", json=update_data)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        course = response.json()
        print("✅ Cours mis à jour avec succès!")
        print(f"Nouveau titre: {course['title']}")
        print(f"Nouveau professeur: {course['professor']}")
        print(f"Nouveaux crédits: {course['credits']}")
        # Vérifier que le code de cours n'a pas changé
        print(f"Code de cours (inchangé): {course['course_code']}")
    else:
        print(f"❌ Échec: {response.text}")


def test_delete_course(course_id):
    """Test de suppression d'un cours."""
    print(f"\n🧪 Test 4: Suppression du cours {course_id}")
    print("=" * 50)

    response = requests.delete(f"{BASE_URL}/{course_id}")
    print(f"Status: {response.status_code}")

    if response.status_code == 204:
        print("✅ Cours supprimé avec succès!")

        # Vérifier que le cours n'existe plus
        get_response = requests.get(f"{BASE_URL}/{course_id}")
        if get_response.status_code == 404:
            print("✅ Confirmation: Le cours n'existe plus (404)")
        else:
            print(f"❌ Le cours existe toujours! Status: {get_response.status_code}")
    else:
        print(f"❌ Échec: {response.text}")


def main():
    """Exécute tous les tests."""
    print("\n" + "=" * 50)
    print("🚀 Tests CRUD pour les cours")
    print("=" * 50)

    # Test 1: Créer un cours
    course_id = test_create_course()

    if not course_id:
        print("\n❌ Impossible de continuer les tests sans ID de cours")
        return

    # Test 2: Récupérer le cours
    test_get_course(course_id)

    # Test 3: Mettre à jour le cours
    test_update_course(course_id)

    # Test 4: Supprimer le cours
    test_delete_course(course_id)

    print("\n" + "=" * 50)
    print("✅ Tous les tests sont terminés!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
