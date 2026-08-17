import os
import warnings
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
print(f"API Key starting chars: {GEMINI_API_KEY[:10] if GEMINI_API_KEY else 'None'}")

try:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    
    print("Listing available models...")
    for m in genai.list_models():
        print(f"Model: {m.name}, Supported Methods: {m.supported_generation_methods}")
except Exception as e:
    import traceback
    traceback.print_exc()
