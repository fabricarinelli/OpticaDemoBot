# app/routers/webhook.py
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks
from app.core.config import settings
from app.services import instagram, gemini, crud
from app.core.database import SessionLocal
from app.services.tools import TOOLS_SCHEMA

router = APIRouter()

# Zona horaria Argentina
TZ_ARG = ZoneInfo("America/Argentina/Cordoba")
now_arg = datetime.now(TZ_ARG)
fecha_actual_str = now_arg.strftime("%A %d de %B de %Y, %H:%Mhs")
# Prompt Base
SYSTEM_PROMPT_BARBERIA = f"""
Sos el asistente virtual de "Barbería Demo". Tu objetivo principal es lograr usar agendar_turno, para eso antes deberas usar registrar_cliente (si hace falta) y consultar_disponibilidad.

### CONTEXTO TEMPORAL (MUY IMPORTANTE):
- **HOY ES:** {fecha_actual_str}
- Usa esta fecha como referencia absoluta para calcular "mañana", "el miércoles", "la semana que viene".
- Si el usuario dice "miercoles" se refiere al proximo miercoles (de esta semana o la que sigue)
_ Nunca agendes turnos para fechas anteriores, o horas ya pasadas del mismo dia.
- No agendes dos turnos para la misma fecha y hora para el mismo cliente, por lo general el cliente quiere un solo turno.

###PREGUNTAS FRECUENTES:
Queda en la ciudad de cordoba, argentina, barrio san martin. La direccion es Castro Barros 1234. El corte sale 12000. El horario de atencion es de martes a domingos de 9 a 20hs.

### PERSONALIDAD:
- Hablá en español argentino, tono urbano, moderno ("Que onda", "Dale", "Quedamos asi", "Bro", "Pana", "Hermano", "Hermanito").
- Sos un empleado del lugar
- No uses la apertura de los signos de exclamacion/interrogacion. Solo el cierre
-No des informacion que no te pidan.
-No trates a los clientes por su nombre, usa bro, pana, hermanito, brody, genio, etc.

### REGLAS DE NEGOCIO (MEMORIA):
1. **Datos del Cliente**: 
   - Si el usuario te da su nombre y teléfono, PRIMERO usá `registrar_cliente`.
   - INMEDIATAMENTE después, si ya tenés fecha y hora pactada, pedile confirmacion y usá `agendar_turno`.

2. **Turnos**:
   - Primero usá `consultar_disponibilidad`.
   - Para confirmar, ejecutá `agendar_turno`.

### REGLA DE ORO (ANTI-MENTIRAS) :
- **PROHIBIDO** decir "Turno agendado", "Te espero", "Listo" o similares SI NO has ejecutado exitosamente la tool `agendar_turno` en este mismo turno.
- Si la tool `agendar_turno` no se ejecutó, NO le mientas al usuario. Decile: "Tengo tus datos, confirmame si querés que cierre la reserva para el [fecha/hora]".
- Si usas la tool `registrar_cliente`, NO asumas que el turno se agendó solo. Tenés que llamar a `agendar_turno` después.
"""


# ==============================================================================
# SISTEMA DE BUFFER (DEBOUNCE)
# ==============================================================================
class MessageBuffer:
    def __init__(self):
        # Almacena los textos: {sender_id: ["Hola", "Quiero turno"]}
        self.buffers = {}
        # Almacena las tareas de espera: {sender_id: Task}
        self.tasks = {}
        # Tiempo de espera en segundos (Ajustado a 15s, 40s puede ser muy lento para chat)
        self.WAIT_TIME = 15

    async def add_message(self, sender_id: str, text: str):
        """
        Recibe un mensaje, lo guarda en el buffer y reinicia el temporizador.
        """
        # 1. Inicializar buffer si no existe
        if sender_id not in self.buffers:
            self.buffers[sender_id] = []

        # 2. Agregar mensaje a la lista
        self.buffers[sender_id].append(text)
        print(f"⏳ Buffer {sender_id}: Mensaje agregado. Esperando {self.WAIT_TIME}s...")

        # 3. Cancelar tarea anterior si existe (reinicio del reloj)
        if sender_id in self.tasks:
            self.tasks[sender_id].cancel()

        # 4. Crear nueva tarea de procesamiento diferido
        self.tasks[sender_id] = asyncio.create_task(self.process_later(sender_id))

    async def process_later(self, sender_id: str):
        """
        Espera X segundos y luego dispara el procesamiento de la IA.
        """
        try:
            await asyncio.sleep(self.WAIT_TIME)

            # Si llegamos acá sin ser cancelados, procesamos todo el bloque
            messages = self.buffers.pop(sender_id, [])
            if messages:
                combined_text = " ".join(messages)  # Unimos todo en un solo string
                print(f"🚀 Procesando bloque para {sender_id}: {combined_text}")
                await process_conversation_block(sender_id, combined_text)

        except asyncio.CancelledError:
            # La tarea fue cancelada porque llegó otro mensaje nuevo. No hacemos nada.
            pass
        finally:
            # Limpieza de la referencia a la tarea
            self.tasks.pop(sender_id, None)


# Instancia global del buffer
buffer_manager = MessageBuffer()


# ==============================================================================
# LÓGICA DE PROCESAMIENTO (IA + DB)
# ==============================================================================
async def process_conversation_block(sender_id: str, user_text: str):
    """
    Esta función se ejecuta SOLO después de que pasó el tiempo de espera.
    Contiene la lógica pesada (Gemini, Tools, DB).
    """
    db = SessionLocal()
    try:
        # 1. Obtener / Crear Cliente
        client = crud.cliente_barberia.get_one(db, ig_id=sender_id)
        if not client:
            client = crud.cliente_barberia.create(db, ig_id=sender_id)

        # NOTA: Los mensajes de usuario ya se guardaron individualmente al llegar
        # (ver 'receive_instagram_message'), así que aquí solo nos preocupamos por responder.

        # 2. Preparar Contexto
        datos_usuario = "No registrados aún."
        if client.nombre or client.telefono:
            datos_usuario = f"Nombre: {client.nombre or 'Falta'}\nTeléfono: {client.telefono or 'Falta'}"

        full_system_prompt = f"{SYSTEM_PROMPT_BARBERIA}\n\n### DATOS DEL CLIENTE ACTUAL (ID: {sender_id}):\n{datos_usuario}"

        history_for_ai = crud.get_chat_history(db, crud.mensaje_barberia.model, client.id)

        # 3. Llamar a Gemini con el texto acumulado
        ai_response_text = await gemini.chat_with_gemini(
            user_message=user_text,
            recipient_id=sender_id,
            db_history=history_for_ai,
            tools_schema=TOOLS_SCHEMA,
            system_instruction=full_system_prompt
        )

        # 4. Responder y Guardar
        if ai_response_text:
            await instagram.send_text(sender_id, ai_response_text)

            now_arg_response = datetime.now(TZ_ARG)
            crud.mensaje_barberia.create(
                db,
                cliente_id=client.id,
                role="model",
                content=ai_response_text,
                timestamp=now_arg_response
            )

    except Exception as e:
        print(f"❌ Error procesando bloque barbería: {e}")
    finally:
        db.close()


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.get("/webhook")
async def verify_webhook(
        mode: str = Query(alias="hub.mode"),
        token: str = Query(alias="hub.verify_token"),
        challenge: str = Query(alias="hub.challenge")
):
    if mode == "subscribe" and token == settings.INSTAGRAM_VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Token incorrecto")


@router.post("/webhook")
async def receive_instagram_message(request: Request):
    """
    Recibe el mensaje, devuelve 200 OK RÁPIDO y delega al buffer.
    """
    try:
        payload = await request.json()
        entry = payload['entry'][0]
        messaging = entry['messaging'][0]
        sender_id = messaging['sender']['id']
        message_data = messaging.get('message', {})

        if message_data.get("is_echo") or 'text' not in message_data:
            return {"status": "ignored"}

        user_text = message_data['text']

        # 1. Guardamos el mensaje en DB INMEDIATAMENTE (Auditoría)
        # Esto asegura que no se pierda nada aunque el bot se reinicie
        db = SessionLocal()
        try:
            client = crud.cliente_barberia.get_one(db, ig_id=sender_id)
            if not client:
                client = crud.cliente_barberia.create(db, ig_id=sender_id)

            crud.mensaje_barberia.create(
                db,
                cliente_id=client.id,
                role="user",
                content=user_text,
                timestamp=datetime.now(TZ_ARG)
            )
        finally:
            db.close()

        await buffer_manager.add_message(sender_id, user_text)

        return {"status": "received"}

    except (IndexError, KeyError):
        return {"status": "ignored"}
    except Exception as e:
        print(f"❌ Error en webhook: {e}")
        return {"status": "error"}