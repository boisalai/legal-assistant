#!/usr/bin/env python3
"""Script pour tester la configuration."""

from config.settings import settings

print("=== Configuration actuelle ===")
print(f"API Host: {settings.api_host}")
print(f"API Port: {settings.api_port}")
print(f"Debug: {settings.debug}")
print(f"\nSurrealDB URL: {settings.surreal_url}")
print(f"Namespace: {settings.surreal_namespace}")
print(f"Database: {settings.surreal_database}")
print(f"\nLLM Provider: {settings.llm_provider}")
print(f"MLX Model: {settings.mlx_model_path}")
print(f"Upload Dir: {settings.upload_dir}")