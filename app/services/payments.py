# app/services/payment.py
import mercadopago
from app.core.config import settings


def generar_link_pago(items: list, external_reference: str, client_email: str = None) -> dict:
    """
    Genera una preferencia de pago en Mercado Pago.

    Args:
        items: Lista de diccionarios [{'title': 'Lente', 'quantity': 1, 'unit_price': 1500.0}]
        external_reference: ID único de tu orden local (para saber quién pagó).
        client_email: Email del comprador (opcional, pre-llena el formulario).

    Returns:
        dict: Con el link de pago (init_point) y el ID de la preferencia.
    """

    # 1. Configurar SDK
    sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)

    # 2. Configurar urls de retorno (A donde vuelve el usuario tras pagar)
    #    Podemos poner tu perfil de IG para que vuelva al chat.
    back_urls = {
        "success": "https://www.instagram.com/",
        "failure": "https://www.instagram.com/",
        "pending": "https://www.instagram.com/"
    }

    # 3. Armar la preferencia
    preference_data = {
        "items": items,
        "payer": {
            "email": client_email or "test_user@test.com"
        },
        "back_urls": back_urls,
        "auto_return": "approved",  # Vuelve automático si se aprueba
        "external_reference": external_reference,  # CLAVE: Esto nos dice qué orden es
        "statement_descriptor": "OPTICA BOT",  # Lo que sale en el resumen de tarjeta
        "expires": True  # Opcional: que el link venza en 1 hora
    }

    try:
        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]

        # init_point = Link para producción
        # sandbox_init_point = Link para pruebas (dinero ficticio)

        return {
            "status": "success",
            "link": preference["init_point"],
            # "link_sandbox": preference["sandbox_init_point"], # Usa este si estás probando con tarjetas fake
            "id": preference["id"]
        }

    except Exception as e:
        print(f"❌ Error al generar link MP: {e}")
        return {"status": "error", "message": str(e)}