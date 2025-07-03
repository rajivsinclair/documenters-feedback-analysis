#!/usr/bin/env python3
"""Check available Gemini models"""

from google import genai

# Initialize client with API key
client = genai.Client(api_key="AIzaSyDPNCzGo0LXmSXXobTs45Mrxeq2kCYG_vg")

print("Available models:")
for model in client.models.list():
    print(f"- {model.name}")
    if hasattr(model, 'supported_generation_methods'):
        print(f"  Supported methods: {model.supported_generation_methods}")
    print()