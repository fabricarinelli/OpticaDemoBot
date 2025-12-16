# app/services/gemini.py
import google.generativeai as genai
from app.core.config import settings
from app.services.tools import handle_tool_call

genai.configure(api_key=settings.GEMINI_API_KEY)


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


def get_model(tools_schema: list, system_instruction: str):
    """
    Crea una instancia del modelo Gemini configurada dinámicamente.
    Permite cambiar de personalidad (Barbería vs Lomitería) al vuelo.
    """
    return genai.GenerativeModel(
        model_name='gemini-2.0-flash',
        tools=[tools_schema] if tools_schema else None,
        system_instruction=system_instruction
    )


async def chat_with_gemini(
        user_message: str,
        recipient_id: str,
        db_history: list = [],
        tools_schema: list = [],
        system_instruction: str = ""
) -> str:
    """
    Función principal dinámica:
    Requiere pasarle los TOOLS y las INSTRUCCIONES específicas del negocio.
    """

    # 1. Instanciamos el modelo con la personalidad correcta
    model = get_model(tools_schema, system_instruction)

    # 2. Iniciamos el chat con historial
    formatted_history = _format_history(db_history)
    chat_session = model.start_chat(history=formatted_history)

    # 3. Enviamos el mensaje del usuario
    try:
        response = await chat_session.send_message_async(user_message)
    except Exception as e:
        print(f"⚠️ Error inicial Gemini: {e}")
        return "Disculpa, estoy teniendo problemas de conexión. ¿Me repetís?"

    # --- BUCLE DE HERRAMIENTAS (Function Calling Loop) ---
    try:
        while True:
            function_call = None
            # Buscamos si Gemini quiere llamar a una función
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        function_call = part.function_call
                        break

            # Si NO hay llamada a función, es respuesta final de texto. Salimos.
            if not function_call:
                break

            tool_name = function_call.name
            tool_args = dict(function_call.args)

            print(f"🤖 Gemini pide usar tool: {tool_name} con args: {tool_args}")

            # 4. Ejecutar la herramienta real
            # (El handle_tool_call ya contiene la lógica de negocio)
            tool_result = await handle_tool_call(tool_name, tool_args, recipient_id)
            print(f"🔧 Resultado Tool: {tool_result}")

            # 5. Devolver el resultado a Gemini para que continue generando la respuesta natural
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