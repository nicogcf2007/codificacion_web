import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment or use fallback
openai_api_key_Codifiacion = os.getenv(
    'OPENAI_API_KEY',
    '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'
)

gemini_api_key = os.getenv('GEMINI_API_KEY', 'AIzaSyDHD-BYapgE7jxFiVt-zbYM84gK6ZpyO2w')