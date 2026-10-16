"""
Model Availability & Access Verification Script for OpenAI API.
Distinguishes:
- Model does not exist (404 NotFoundError)
- Model exists but project/key lacks access (403 PermissionDeniedError)
- Invalid API Key (401 AuthenticationError)
- Successful access (200 OK)
Never exposes the API key.
"""

import os
import sys
from pathlib import Path

# Ensure code directory is in sys.path
CODE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE_DIR))

import config

def verify_model_access(model_id: str = "gpt-5.4-mini"):
    print("=" * 65)
    print(f" OPENAI API MODEL ACCESS VERIFICATION: {model_id}")
    print("=" * 65)

    api_key = config.OPENAI_API_KEY.strip() if config.OPENAI_API_KEY else ""

    if not api_key:
        print("[STATUS] OPENAI_API_KEY is currently EMPTY in .env.")
        print("[CONFIG] Configured Vision Model :", config.VISION_MODEL)
        print("[CONFIG] Configured NLP Model    :", config.NLP_MODEL)
        print("\n[ACTION REQUIRED] Please enter your OpenAI API key in .env:")
        print("    OPENAI_API_KEY=sk-your-key-here")
        print("\nOnce saved, re-run this script to execute the live access test.")
        return False, "KEY_EMPTY"

    print("[STATUS] API key is configured.")
    print(f"[STATUS] Testing access to model: '{model_id}'...")

    try:
        from openai import OpenAI, NotFoundError, PermissionDeniedError, AuthenticationError
        client = OpenAI(api_key=api_key)

        # 1. Test model retrieval
        try:
            model_obj = client.models.retrieve(model_id)
            print(f"\n[SUCCESS] Model '{model_id}' EXISTS and is accessible on this account!")
            print(f"          Model ID: {model_obj.id}, Created: {getattr(model_obj, 'created', 'N/A')}")
            
            # Test minimal inference ping
            resp = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1
            )
            print(f"[SUCCESS] Inference test succeeded! Response received from {model_id}.")
            return True, "ACCESSIBLE"

        except NotFoundError as e:
            print(f"\n[RESULT: 404 NOT FOUND] The model '{model_id}' DOES NOT EXIST in the OpenAI API.")
            print(f"Details: {e.message if hasattr(e, 'message') else str(e)}")
            _list_available_models(client)
            return False, "MODEL_DOES_NOT_EXIST"

        except PermissionDeniedError as e:
            print(f"\n[RESULT: 403 PERMISSION DENIED] The model '{model_id}' EXISTS, but this API key/project LACKS ACCESS.")
            print(f"Details: {e.message if hasattr(e, 'message') else str(e)}")
            _list_available_models(client)
            return False, "KEY_LACKS_ACCESS"

        except AuthenticationError as e:
            print(f"\n[RESULT: 401 AUTHENTICATION ERROR] Invalid OpenAI API Key.")
            print(f"Details: {e.message if hasattr(e, 'message') else str(e)}")
            return False, "AUTH_ERROR"

    except Exception as e:
        err_type = type(e).__name__
        err_msg = str(e)
        if "404" in err_msg or "NotFoundError" in err_type or "does not exist" in err_msg:
            print(f"\n[RESULT: 404 NOT FOUND] The model '{model_id}' DOES NOT EXIST in the OpenAI API.")
            print(f"Details: {err_msg}")
            return False, "MODEL_DOES_NOT_EXIST"
        elif "403" in err_msg or "PermissionDeniedError" in err_type:
            print(f"\n[RESULT: 403 PERMISSION DENIED] The model '{model_id}' EXISTS, but this API key/project LACKS ACCESS.")
            print(f"Details: {err_msg}")
            return False, "KEY_LACKS_ACCESS"
        else:
            print(f"\n[RESULT: API ERROR] {err_type}: {err_msg}")
            return False, "API_ERROR"

def _list_available_models(client):
    try:
        print("\nQuerying accessible models on your account...")
        models = client.models.list()
        relevant = [m.id for m in models.data if any(w in m.id for w in ["gpt", "mini", "o1", "o3", "4o"])]
        print(f"Found {len(relevant)} accessible model(s) matching ['gpt', 'mini', 'o1', 'o3', '4o']:")
        for mid in sorted(relevant)[:20]:
            print(f"  - {mid}")
    except Exception as e:
        print(f"Could not list models: {e}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else config.DEFAULT_MODEL
    verify_model_access(target)
