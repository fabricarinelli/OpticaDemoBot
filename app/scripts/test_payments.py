# app/scripts/test_payment.py
import sys
import os
import uuid # Para generar IDs únicos de prueba
from dotenv import load_dotenv

# Path fix para importar app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
load_dotenv()

from app.services.payments import generar_link_pago

def probar_mercado_pago():
    print("💰 TEST DE MERCADO PAGO")
    print("=" * 50)

    # 1. Simular Items del Carrito
    # La IA nos pasará esto cuando el usuario diga "quiero comprar esos lentes"
    items_carrito = [
        {
            "title": "Líquido Renu 500ml",
            "quantity": 1,
            "unit_price": 15000.0,
            "currency_id": "ARS"
        },
        {
            "title": "Estuche Rígido",
            "quantity": 2,
            "unit_price": 4500.0,
            "currency_id": "ARS"
        }
    ]

    # Referencia única (simulando un ID de orden de tu base de datos)
    id_orden_ficticia = f"ORD-{uuid.uuid4().hex[:8]}"

    print(f"🛒 Generando link para orden: {id_orden_ficticia}")
    print(f"📦 Items: {len(items_carrito)}")

    # 2. Llamar al servicio
    resultado = generar_link_pago(items_carrito, id_orden_ficticia)

    # 3. Resultado
    if resultado["status"] == "success":
        print("\n✅ ¡ÉXITO! Link generado:")
        print("-" * 50)
        print(f"🔗 LINK DE PAGO: {resultado['link']}")
        print("-" * 50)
        print("💡 Haz clic (o Ctrl+Clic) para ver el checkout real de MP.")
    else:
        print(f"\n❌ FALLÓ: {resultado.get('message')}")

if __name__ == "__main__":
    probar_mercado_pago()