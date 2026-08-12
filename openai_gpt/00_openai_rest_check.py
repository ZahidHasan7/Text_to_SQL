# 00_openai_rest_check.py
# Simple connectivity & quota smoke test for OpenAI gpt-4o-mini
import os
from dotenv import load_dotenv
import json

load_dotenv()

from openai_gpt.utils_openai_rest import openai_generate_text, OPENAI_API_KEY

def main():
    print("[i] OPENAI_API_KEY present:", bool(OPENAI_API_KEY))
    if not OPENAI_API_KEY:
        print("[ERR] Missing OPENAI_API_KEY; aborting.")
        return
    prompt = "Return only this SQL: SELECT 1;"
    try:
        text, model = openai_generate_text(prompt, return_model=True, temperature=0.0, max_output_tokens=50)
        print(f"[OK] Model={model} ->", text.strip())
    except Exception as e:
        print("[FAIL] OpenAI call error:", repr(e))

if __name__ == "__main__":
    main()
