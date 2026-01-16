"""
Tests d'intégration pour l'authentification.
"""

import pytest
from httpx import AsyncClient

# Test data
TEST_EMAIL = "auth_test@example.com"
TEST_PASSWORD = "testpassword123"
TEST_NAME = "Auth Test User"

class TestAuth:
    """Tests pour les endpoints d'authentification."""
    
    @pytest.mark.asyncio
    async def test_register_flow(self, client: AsyncClient):
        """Test le flux complet d'inscription et de connexion."""
        # 1. Inscription
        register_data = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "name": TEST_NAME
        }
        response = await client.post("/api/auth/register", json=register_data)
        
        # Si l'utilisateur existe déjà (tests précédents), c'est ok
        if response.status_code == 400 and "déjà associé" in response.text:
            pass
        else:
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Compte créé avec succès"
            assert data["user"]["email"] == TEST_EMAIL
            assert data["user"]["nom"] == TEST_NAME

        # 2. Connexion
        login_data = {
            "username": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        response = await client.post(
            "/api/auth/login", 
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        token_data = response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        
        token = token_data["access_token"]
        
        # 3. Vérification du token (Me)
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        user_data = response.json()
        assert user_data["email"] == TEST_EMAIL
        
        # 4. Deconnexion
        response = await client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        # 5. Vérification du token invalide après logout
        # Note: L'implémentation actuelle utilise une mémoire locale pour les sessions
        # qui n'est pas partagée entre les processus workers si uvicorn lance plusieurs.
        # Mais en mode test, c'est le même processus ou la session est gérée.
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test la connexion avec des identifiants invalides."""
        login_data = {
            "username": "wrong@example.com",
            "password": "wrongpassword"
        }
        response = await client.post(
            "/api/auth/login", 
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_password_reset_flow(self, client: AsyncClient):
        """Test le flux de réinitialisation de mot de passe."""
        # 1. Demande de réinitialisation
        response = await client.post(
            "/api/auth/forgot-password",
            json={"email": TEST_EMAIL}
        )
        assert response.status_code == 200
        # Pour des raisons de sécurité, on ne doit pas savoir si l'email existe ou non
        # mais dans ce test on sait qu'il existe (créé dans test_register_flow ou avant)
        
        # TODO: Pour tester pleinement le reset, il faudrait mocker send_reset_email
        # ou avoir un moyen d'accéder aux tokens stockés en mémoire (difficile en test d'intégration
        # car le serveur tourne dans un processus séparé).
        # Pour l'instant, on vérifie juste que l'endpoint répond correctement.

    @pytest.mark.asyncio
    async def test_register_invalid_data(self, client: AsyncClient):
        """Test l'inscription avec des données invalides."""
        # Mot de passe trop court
        response = await client.post("/api/auth/register", json={
            "email": "short@test.com",
            "password": "short",
            "name": "Short Pass"
        })
        assert response.status_code == 400
        
        # Nom trop court
        response = await client.post("/api/auth/register", json={
            "email": "nameless@test.com",
            "password": "password123",
            "name": "a"
        })
        assert response.status_code == 400
