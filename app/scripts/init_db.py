# app/scripts/init_db.py
import sys
import os
import random
from datetime import datetime, timedelta

# Hack para importar app desde la carpeta scripts
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import Base, engine, SessionLocal
from app.models.models import (
    MenuLomiteria, ClienteLomiteria, PedidoLomiteria, ItemPedidoLomiteria,
    ClienteBarberia, TurnoBarberia
)


def init_db():
    print("🔄 Reiniciando Base de Datos...")

    # Opcional: Eliminar tablas viejas para empezar limpio
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # ==========================================
    # 1. CARGA DEL MENÚ LOMITERÍA
    # ==========================================
    print("🍔 Cargando Menú de Lomitería...")

    menu_items = [
        # --- LOMITOS ---
        MenuLomiteria(nombre="Lomo Completo", precio=14000,
                      descripcion="Pan casero, bife de lomo, huevo, queso, jamón, lechuga, tomate y mayonesa de la casa. Sale con papas."),
        MenuLomiteria(nombre="Lomo Árabe", precio=13500,
                      descripcion="Pan árabe tostado, carne vacuna en tiritas, tomate, lechuga, salsa criolla y mayonesa."),
        MenuLomiteria(nombre="Lomo de Pollo", precio=12000,
                      descripcion="Pan casero, pechuga de pollo grillada, queso tybo, huevo, tomate y lechuga."),
        MenuLomiteria(nombre="Lomo Veggie", precio=11500,
                      descripcion="Pan integral, medallón de lentejas, queso, palta, rúcula, tomate y huevo."),

        # --- PIZZAS (5 gustos) ---
        MenuLomiteria(nombre="Pizza Muzzarella", precio=9000,
                      descripcion="Salsa de tomate, doble muzzarella, orégano y aceitunas verdes."),
        MenuLomiteria(nombre="Pizza Especial", precio=11000,
                      descripcion="Muzzarella, jamón cocido, morrones asados y huevo duro."),
        MenuLomiteria(nombre="Pizza Rúcula y Crudo", precio=12500,
                      descripcion="Base de muzzarella, jamón crudo, rúcula fresca y parmesano."),
        MenuLomiteria(nombre="Pizza Calabresa", precio=10500,
                      descripcion="Muzzarella y rodajas de longaniza calabresa picante."),
        MenuLomiteria(nombre="Pizza Fugazzeta", precio=10000,
                      descripcion="Masa media, mucha cebolla, queso muzzarella y un toque de parmesano gratinado."),

        # --- EMPANADAS ---
        MenuLomiteria(nombre="Empanada Carne Suave", precio=1200,
                      descripcion="Carne molida especial, cebolla, huevo y aceituna. Frita o al horno."),
        MenuLomiteria(nombre="Empanada Carne Picante", precio=1200,
                      descripcion="Cortada a cuchillo, con ají molido y pimentón."),
        MenuLomiteria(nombre="Empanada Jamón y Queso", precio=1200, descripcion="Clásica de jamón y muzzarella."),
        MenuLomiteria(nombre="Empanada Pollo", precio=1200, descripcion="Pollo desmenuzado con salsa blanca y verdeo."),
        # Packs para facilitar la venta
        MenuLomiteria(nombre="Docena de Empanadas (Surtidas)", precio=12000,
                      descripcion="12 empanadas a elección (ahorrás el precio de 2)."),
        MenuLomiteria(nombre="Media Docena Empanadas", precio=6500, descripcion="6 empanadas a elección."),

        # --- BEBIDAS ---
        MenuLomiteria(nombre="Coca Cola 1.5L", precio=3500, descripcion="Botella descartable."),
        MenuLomiteria(nombre="Cerveza Andes Rubia 1L", precio=4500,
                      descripcion="Botella retornable (te cobramos el envase si no tenés)."),
        MenuLomiteria(nombre="Agua Sin Gas 500ml", precio=1500, descripcion="Botella personal."),

        # --- PROMOCIONES ---
        MenuLomiteria(nombre="Promo Pareja", precio=26000,
                      descripcion="2 Lomos Completos + 1 Coca Cola 1.5L + Porción extra de papas."),
        MenuLomiteria(nombre="Promo Pizza Party", precio=18000,
                      descripcion="1 Pizza Especial + 1 Pizza Muzza + 1 Cerveza 1L.")
    ]

    db.add_all(menu_items)
    db.commit()

    # ==========================================
    # 2. CARGA DE CLIENTES DE PRUEBA
    # ==========================================
    print("👥 Creando Clientes Ficticios...")

    # Cliente Lomitería
    c_lomi1 = ClienteLomiteria(ig_id="123456789", nombre="Juan Perez", telefono="3511112222",
                               direccion="Av. Colon 1200")
    c_lomi2 = ClienteLomiteria(ig_id="987654321", nombre="Maria Garcia", telefono="3513334444",
                               direccion="Chacabuco 500")

    # Cliente Barbería
    c_barber1 = ClienteBarberia(ig_id="111222333", nombre="Carlos Tevez", telefono="3515556666")

    db.add_all([c_lomi1, c_lomi2, c_barber1])
    db.commit()

    # ==========================================
    # 3. CARGA DE PEDIDOS HISTÓRICOS (LOMITERÍA)
    # ==========================================
    print("🛒 Generando Historial de Pedidos...")

    # Recuperamos los items para usarlos
    lomo = db.query(MenuLomiteria).filter_by(nombre="Lomo Completo").first()
    coca = db.query(MenuLomiteria).filter_by(nombre="Coca Cola 1.5L").first()
    pizza = db.query(MenuLomiteria).filter_by(nombre="Pizza Rúcula y Crudo").first()

    # Pedido 1: Aprobado hace 2 días
    pedido1 = PedidoLomiteria(
        cliente_id=c_lomi1.id,
        estado="aprobado",
        total=(lomo.precio * 2) + coca.precio,
        fecha=datetime.now() - timedelta(days=2),
        mp_payment_link="https://mp.fake/paid"
    )
    db.add(pedido1)
    db.commit()  # Necesitamos el ID del pedido

    item1 = ItemPedidoLomiteria(pedido_id=pedido1.id, producto_id=lomo.id, cantidad=2, precio_unitario=lomo.precio,
                                aclaraciones="Uno sin tomate")
    item2 = ItemPedidoLomiteria(pedido_id=pedido1.id, producto_id=coca.id, cantidad=1, precio_unitario=coca.precio)
    db.add_all([item1, item2])

    # Pedido 2: Carrito abierto (Pendiente)
    pedido2 = PedidoLomiteria(
        cliente_id=c_lomi2.id,
        estado="carrito",
        total=pizza.precio,
        fecha=datetime.now()
    )
    db.add(pedido2)
    db.commit()

    item3 = ItemPedidoLomiteria(pedido_id=pedido2.id, producto_id=pizza.id, cantidad=1, precio_unitario=pizza.precio)
    db.add(item3)

    db.commit()

    # ==========================================
    # 4. CARGA DE TURNOS HISTÓRICOS (BARBERÍA)
    # ==========================================
    print("💈 Generando Turnos de Prueba...")

    turno1 = TurnoBarberia(
        cliente_id=c_barber1.id,
        fecha_hora=datetime.now() + timedelta(days=1, hours=2),  # Mañana
        estado="activo",
        google_event_id="evento_falso_google_123",
        nota="Corte degradé"
    )
    db.add(turno1)
    db.commit()

    print("✅ ¡Base de datos inicializada con éxito!")
    print(f"   - {len(menu_items)} productos en el menú.")
    print("   - Clientes y pedidos de prueba creados.")
    db.close()


if __name__ == "__main__":
    init_db()