#!/usr/bin/env python3
"""Test provider and model resolution"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Test provider resolution
from agents.base import get_provider, get_model_name, _resolve_provider

print(f"=== Provider Resolution Test ===\n")

print(f"MODAL_API_KEY set: {'MODAL_API_KEY' in os.environ}")
print(f"NIM_API_KEY set: {'NIM_API_KEY' in os.environ}")
print(f"GROQ_API_KEY set: {'GROQ_API_KEY' in os.environ}")
print(f"GEMINI_API_KEY set: {'GEMINI_API_KEY' in os.environ}")

print(f"\nResolved provider: {get_provider()}")
print(f"Default model: {get_model_name()}")
print(f"Specified model override: {get_model_name('custom-model')}")

print(f"\n=== Done ===")
