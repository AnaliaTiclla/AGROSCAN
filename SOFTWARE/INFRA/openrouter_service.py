import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
if API_KEY:
    API_KEY = API_KEY.strip().replace('"', '').replace("'", "")

# Modelos validados como gratuitos y disponibles (al 2025-02-19)
MODEL = "stepfun/step-3.5-flash:free"  # Modelo rápido y gratuito
FALLBACK_MODEL = "openrouter/free"     # Meta-modelo que enruta a cualquier gratuito disponible
API_URL = "https://openrouter.ai/api/v1/chat/completions"

def verificar_conexion():
    """Verifica si hay conexión a internet haciendo ping a OpenRouter."""
    try:
        requests.get("https://openrouter.ai", timeout=3)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False

def consultar_chatbot(pregunta, contexto_imagen):
    """
    Consulta al modelo de OpenRouter con el contexto de la imagen.
    Incluye reintentos para error 429 y fallback a modelo secundario.
    """
    if not API_KEY:
        return "Error: No se encontró la API Key de OpenRouter."

    if not verificar_conexion():
        return "No estás conectado a internet para esta función."

    # Construir el prompt del sistema (Corpus)
    system_prompt = (
        "Eres AgroScan IA, un asistente experto en el cultivo y análisis de espárragos. "
        "Tu función es ayudar al agricultor basándote en la imagen analizada y tus conocimientos sobre espárragos. "
        "Reglas estrictas:\n"
        "1. Solo responde preguntas sobre espárragos, agricultura relacionada con espárragos, o sobre la imagen analizada.\n"
        "2. Si el usuario saluda (hola, buenos días, etc.), responde amablemente y pregunta en qué puedes ayudar con sus cultivos.\n"
        "3. Si la pregunta NO es un saludo y NO tiene que ver con espárragos o la imagen, responde EXACTAMENTE: 'No te estoy entendiendo... reformula la pregunta'.\n"
        "4. Habla siempre en español.\n"
        "5. Sé conciso, claro y profesional. RESPONDE SIEMPRE EN UN SOLO PÁRRAFO.\n"
        "6. Usa el contexto de la imagen proporcionado para dar respuestas precisas sobre lo que se ve."
    )

    # Construir el contexto del usuario
    detalles_imagen = (
        f"Contexto de la imagen analizada por YOLO:\n"
        f"- Espárragos sanos detectados: {contexto_imagen.get('sanos', 0)}\n"
        f"- Espárragos enfermos detectados: {contexto_imagen.get('enfermos', 0)}\n"
        f"- Total detectados: {contexto_imagen.get('total', 0)}\n"
        f"- Etiquetas detectadas: {contexto_imagen.get('resumen_texto', 'Ninguna')}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{detalles_imagen}\n\nPregunta del usuario: {pregunta}"}
    ]

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://agroscan.local",
        "X-Title": "AgroScan Desktop"
    }

    # Función auxiliar para hacer la petición
    def _hacer_peticion(modelo_a_usar):
        payload = {
            "model": modelo_a_usar,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500
        }
        resp = requests.post(API_URL, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.json()

    # Estrategia: Reintentar principal si es 429, sino pasar a fallback
    
    # 1. Intentos con Modelo Principal
    for i in range(2):
        try:
            data = _hacer_peticion(MODEL)
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                if content:
                    return content.strip()
                else:
                    print(f"Advertencia: Modelo {MODEL} retornó contenido vacío.")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"Modelo principal saturado (429). Reintentando en 2s... (Intento {i+1}/2)")
                time.sleep(2)
                continue
            else:
                print(f"Error en modelo principal ({e}). Pasando a fallback.")
                break # Salir para probar fallback
        except Exception as e:
            print(f"Error inesperado en modelo principal: {e}")
            break

    # 2. Intento con Modelo de Respaldo (Fallback)
    print(f"Usando modelo de respaldo: {FALLBACK_MODEL}")
    try:
        data = _hacer_peticion(FALLBACK_MODEL)
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"]["content"]
            if content:
                return content.strip() + "\n(Respuesta generada por modelo de respaldo)"
            else:
                return "Error: La IA generó una respuesta vacía."
    except requests.exceptions.HTTPError as e:
        print(f"Error en fallback: {e}")
        try:
            print(f"Detalle error fallback: {e.response.text}")
        except:
            pass
            
        if e.response.status_code == 429:
            return "Todos los servicios de IA están saturados. Intenta en 1 minuto."
        return "Error técnico en el servicio de IA."
            
    except requests.exceptions.RequestException as e:
        print(f"Error conexión fallback: {e}")
        return "Error de conexión con el servicio de IA."
    
    return "Error: No se recibió respuesta válida."
