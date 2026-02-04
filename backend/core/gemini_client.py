import os
import sys
import time
from google import genai
from google.genai import types

# Import API key from config
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from config import gemini_api_key

# Model Selection
# User requested "Gemini 3 Flash". 
MODEL_NAME = "gemini-3-flash-preview"

def request_gemini(messages, temperature=0.0, max_retries=3):
    """
    Make a request to Gemini API with robust error handling and retries.
    """
    system_instruction = None
    user_prompt = ""
    
    for msg in messages:
        if msg['role'] == 'system':
            system_instruction = msg['content']
        elif msg['role'] == 'user':
            user_prompt += msg['content'] + "\n"

    for attempt in range(max_retries):
        try:
            # Re-initialize client per request to avoid stale connection/SSL issues
            # Using 120000 milliseconds (120 seconds) for http_options 'timeout'
            # The library seems to interpret int as ms or requires >10s?
            # Error message says "Manually set deadline 1s is too short. Minimum allowed deadline is 10s."
            # This suggests that passing '120' might be interpreted as seconds but something is overriding it or unit is wrong.
            # Let's try removing explicit timeout for now or setting it very high if it expects milliseconds.
            # However, google-genai doc usually says seconds.
            # The error "Manually set deadline 1s" is very strange if we passed 120.
            # It might be that 'timeout' key in http_options is not the correct way for this client version?
            # Or maybe it conflicts with some internal default.
            
            # Let's try initializing WITHOUT http_options first to see if default works, 
            # as the library should handle defaults better than our manual overrides which are failing.
            client = genai.Client(api_key=gemini_api_key) 
            
            # Alternatively, if we MUST set timeout, let's try setting it on the generate_content config if supported,
            # or rely on default. The previous error was SSL handshake timeout (network), now it's Invalid Argument (config).
            # Let's revert to standard client init.
            
            print(f"[Gemini] Intentando conectar con Google API (Intento {attempt+1})...")

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    system_instruction=system_instruction
                )
            )
            
            # DEBUG: Print full response
            print(f"\n[Gemini] Solicitud exitosa (Intento {attempt+1})")
            print("="*50)
            print("[Gemini] RAW RESPONSE OBJECT:")
            print(response)
            try:
                # Attempt to print JSON structure if possible, for clarity
                # Note: response might not be directly serializable, but printing 'response' usually works
                pass
            except:
                pass
            print("="*50)

            if hasattr(response, 'text') and response.text:
                return response.text
            else:
                print(f"[Gemini] Respuesta sin texto (posible bloqueo de seguridad): {response}")
                return None

        except Exception as e:
            print(f"\n[Gemini] Error en intento {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                wait_time = 5 * (attempt + 1) # Exponential backoff: 5s, 10s, 15s
                print(f"[Gemini] Reintentando en {wait_time} segundos...")
                time.sleep(wait_time)
            else:
                print("[Gemini] Fallaron todos los intentos.")
                return None
    return None