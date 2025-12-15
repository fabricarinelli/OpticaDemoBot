# app/services/gemini_service.py
import google.generativeai as genai
from google.generativeai.types import content_types
from collections.abc import Iterable

from app.core.config import settings
from app.services.tools import TOOLS_SCHEMA, handle_tool_call

# 1. Configurar la API Key
genai.configure(api_key=settings.GEMINI_API_KEY)

# 2. Configuración del Modelo
# Definimos las instrucciones de sistema para que sepa cómo comportarse y usar la memoria
model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    tools=[TOOLS_SCHEMA],
    system_instruction="""
    Sos 'OpticaBot', asistente de óptica. Tu misión es concretar ventas y turnos.

    REGLAS DE ORO DE CONTEXTO (MEMORIA):
    1. Si el usuario responde a una oferta tuya (ej: "a las 9"), ASUME que se refiere a la fecha y profesional que TÚ acabas de mencionar. NO preguntes de nuevo fecha ni profesional.
    2. Si ya sabes que el usuario quiere 'Optico' por mensajes anteriores, no lo vuelvas a preguntar.
    3. Solo pide el NOMBRE del cliente al final, justo antes de llamar a 'agendar_turno'.

    REGLAS DE TOOLS:
    1. Usa 'consultar_disponibilidad' si te piden horarios.
    2. Usa 'agendar_turno' SOLO cuando tengas: Profesional, Fecha/Hora exacta y Nombre.
    3. Si falta el nombre, pídelo: "¿A nombre de quién anoto el turno?".
    """
)


def _format_history(db_messages: list) -> list:
    """
    Convierte los mensajes de la Base de Datos al formato que pide Gemini.
    DB: Objeto Message(role='user', content='...')
    Gemini: {'role': 'user', 'parts': ['...']}
    """
    history = []
    for msg in db_messages:
        # Mapeamos 'assistant' o 'model' de tu DB al rol 'model' de Gemini
        # (A veces en la DB se guarda como 'assistant' si usas otros sistemas, aquí unificamos)
        role = "user" if msg.role == "user" else "model"

        # Filtramos mensajes vacíos o nulos para que no rompa la API
        if msg.content:
            history.append({"role": role, "parts": [msg.content]})
    return history


async def chat_with_gemini(user_message: str, recipient_id: str, db_history: list = []) -> str:
    """
    Función principal:
    1. Inicia chat cargando el HISTORIAL (db_history).
    2. Envía mensaje del usuario.
    3. Si Gemini pide ejecutar función -> La ejecutamos -> Le damos el resultado.
    4. Devuelve el texto final para el usuario.
    """

    # Convertimos tu historial de SQL a formato Gemini y se lo pasamos al iniciar el chat
    formatted_history = _format_history(db_history)
    chat_session = model.start_chat(history=formatted_history)
    # ----------------------------------------

    # Enviamos el mensaje del usuario
    response = await chat_session.send_message_async(user_message)

    # --- BUCLE DE HERRAMIENTAS (Function Calling Loop) ---
    try:
        # Iteramos mientras Gemini quiera seguir llamando funciones
        while response.candidates[0].content.parts[0].function_call:
            # 1. Detectar qué función quiere llamar
            function_call = response.candidates[0].content.parts[0].function_call
            tool_name = function_call.name
            tool_args = dict(function_call.args)

            print(f"🤖 Gemini pide usar tool: {tool_name} con args: {tool_args}")

            # 2. Ejecutar la herramienta real (usando tu ia_tools.py)
            tool_result = await handle_tool_call(tool_name, tool_args, recipient_id)

            print(f"🔧 Resultado Tool: {tool_result}")

            # 3. Devolver el resultado a Gemini
            response = await chat_session.send_message_async(
                genai.protos.Content(
                    parts=[genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=tool_name,
                            response={'result': tool_result}
                        )
                    )]
                )
            )
    except Exception as e:
        print(f"⚠️ Error en el bucle de tools: {e}")
        return "Disculpa, tuve un error procesando tu solicitud. ¿Podrías intentar de nuevo?"

    # Devolvemos el texto final
    return response.text