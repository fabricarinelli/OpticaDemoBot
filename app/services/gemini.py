import google.generativeai as genai
from app.core.config import settings
from app.services.tools import TOOLS_SCHEMA, handle_tool_call

# 1. Configurar la API Key
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    tools=[TOOLS_SCHEMA],
    system_instruction="""
    Te vas a comunicar como si fueras un empleado de Optica Demo, fingiendo no ser un bot. 

    REGLAS DE ORO DE CONTEXTO (MEMORIA):
    1- Intenta pedir todos los datos para usar una tool en un solo mensaje, revisando antes que no se puedan sacar del
    historial
    2- Habla en español argentino y relajado, pero sin faltar el respeto pues eres un negocio.

    REGLAS DE TOOLS:
    1. Usa 'consultar_disponibilidad' si te piden horarios para turnos.
    2. Usa 'agendar_turno' SOLO cuando tengas: Profesional, Fecha/Hora exacta y Nombre.
    3. Si se sabe que hay que usar una tool, pero faltan datos, pedirlos amablemente.
    """
)


def _format_history(db_messages: list) -> list:
    """
    Convierte los mensajes de la Base de Datos al formato que pide Gemini.
    """
    history = []
    for msg in db_messages:
        role = "user" if msg.role == "user" else "model"
        if msg.content:
            history.append({"role": role, "parts": [msg.content]})
    return history


async def chat_with_gemini(user_message: str, recipient_id: str, db_history: list = []) -> str:
    """
    Función principal:
    1. Inicia chat cargando el HISTORIAL.
    2. Envía mensaje del usuario.
    3. Si Gemini pide ejecutar función -> La ejecutamos -> Le damos el resultado.
    4. Devuelve el texto final para el usuario.
    """
    formatted_history = _format_history(db_history)
    chat_session = model.start_chat(history=formatted_history)

    # Enviamos el mensaje del usuario
    response = await chat_session.send_message_async(user_message)

    # --- BUCLE DE HERRAMIENTAS (Function Calling Loop) ---
    try:
        while True:
            function_call = None
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    function_call = part.function_call
                    break

            # Si NO encontramos función en ninguna parte, asumimos que es respuesta final de texto
            if not function_call:
                break

            tool_name = function_call.name
            tool_args = dict(function_call.args)

            print(f"🤖 Gemini pide usar tool: {tool_name} con args: {tool_args}")

            # 3. Ejecutar la herramienta real
            tool_result = await handle_tool_call(tool_name, tool_args, recipient_id)
            print(f"🔧 Resultado Tool: {tool_result}")

            # 4. Devolver el resultado a Gemini para que continue generando
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

    return response.text