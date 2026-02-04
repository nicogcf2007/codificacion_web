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

# Global client instance
_client_instance = None

def get_client(reset=False):
    global _client_instance
    if _client_instance is None or reset:
        print("[Gemini] Inicializando cliente de Google GenAI...")
        # Configurar timeout explícito de 120 segundos para evitar bloqueos
        _client_instance = genai.Client(api_key=gemini_api_key, http_options={'timeout': 120})
    return _client_instance

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
            # Reutilizar cliente, resetear solo si es un reintento (fallo previo)
            # Esto evita crear miles de conexiones/clientes en bucles rápidos
            should_reset = (attempt > 0)
            client = get_client(reset=should_reset)
            
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
            
            # Si falla, forzamos reinicio del cliente en el siguiente intento
            
            if attempt < max_retries - 1:
                wait_time = 5 * (attempt + 1) # Exponential backoff: 5s, 10s, 15s
                print(f"[Gemini] Reintentando en {wait_time} segundos...")
                time.sleep(wait_time)
            else:
                print("[Gemini] Fallaron todos los intentos.")
                return None
    return None
