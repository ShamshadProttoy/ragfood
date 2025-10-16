"""
Configuration constants for the RAG-Food system.

Centralizes tunables to avoid scattering magic strings across the codebase.
"""

import os

# Storage / Data
CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "foods"
JSON_FILE = "foods.json"

# Models
EMBED_MODEL = "mxbai-embed-large"
LLM_MODEL = "llama3.2"

# Services
OLLAMA_HOST = "http://localhost:11434"

# Network
HTTP_TIMEOUT_SECONDS = 30

# Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.1-8b-instant"
