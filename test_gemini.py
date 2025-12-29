import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("MISSING_API_KEY")
else:
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents="test"
        )
        print("GEMINI_OK:", response.text)
    except Exception as e:
        print("GEMINI_ERROR:", str(e))
