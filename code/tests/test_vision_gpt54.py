import sys
sys.path.insert(0, "code")
import base64, json, config
from openai import OpenAI
from pathlib import Path

client = OpenAI(api_key=config.OPENAI_API_KEY)
img_path = Path("dataset/media/images/image_01.png")
with open(img_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")

try:
    resp = client.chat.completions.create(
        model="gpt-5.4",
        messages=[
            {"role": "system", "content": 'Extract net payable amount and 3-letter currency code as JSON: {"amount": float, "currency": str}'},
            {"role": "user", "content": [
                {"type": "text", "text": "Extract net amount and currency."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}}
            ]}
        ],
        response_format={"type": "json_object"},
        max_completion_tokens=200
    )
    print("gpt-5.4 Vision test SUCCESS!")
    print("Response:", resp.choices[0].message.content)
    print("Usage:", resp.usage)
except Exception as e:
    print("Vision test FAILED:", type(e).__name__, e)