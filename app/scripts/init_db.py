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
    print("🔄 INICIANDO RESET DE BASE DE DATOS...")

    # 1. Limpieza y Re-creación de Tablas
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # ==========================================
        # 1. CARGA DEL MENÚ LOMITERÍA (BIEN POBLADO)
        # ==========================================
        print("🍔 Cargando Menú Extendido...")

        menu_items = [
            # --- LOMITOS ---
            MenuLomiteria(nombre="Lomo Completo", precio=14500,
                          descripcion="Pan casero, bife de lomo tierno, huevo, queso tybo, jamón cocido, lechuga, tomate y mayonesa casera. Con papas."),
            MenuLomiteria(nombre="Lomo Árabe", precio=13800,
                          descripcion="Pan árabe tostado, carne vacuna en tiritas, tomate, lechuga, salsa criolla y mayonesa de ajo."),
            MenuLomiteria(nombre="Lomo de Pollo", precio=12500,
                          descripcion="Pan casero, pechuga de pollo grillada, queso, huevo, tomate, lechuga y salsa suave."),
            MenuLomiteria(nombre="Lomo Veggie", precio=11500,
                          descripcion="Pan integral, medallón de lentejas y arroz yamaní, queso, palta, rúcula, tomate y huevo."),
            MenuLomiteria(nombre="Lomo La Bestia (Doble)", precio=19000,
                          descripcion="Doble carne, doble queso, doble huevo, panceta crocante y barbacoa."),

            # --- HAMBURGUESAS ---
            MenuLomiteria(nombre="Hamburguesa Clásica", precio=9500,
                          descripcion="Medallón 180g, lechuga, tomate, queso cheddar."),
            MenuLomiteria(nombre="Hamburguesa Americana", precio=11000,
                          descripcion="Medallón 180g, cheddar, panceta, cebolla caramelizada y barbacoa."),

            # --- PIZZAS ---
            MenuLomiteria(nombre="Pizza Muzzarella", precio=9200,
                          descripcion="Salsa de tomate, doble muzzarella, orégano y aceitunas."),
            MenuLomiteria(nombre="Pizza Especial", precio=11500,
                          descripcion="Muzzarella, jamón cocido natural, morrones asados y huevo duro."),
            MenuLomiteria(nombre="Pizza Rúcula y Crudo", precio=13000,
                          descripcion="Muzzarella, jamón crudo estacionado, rúcula fresca y hebras de parmesano."),
            MenuLomiteria(nombre="Pizza Calabresa", precio=10800,
                          descripcion="Muzzarella y rodajas de longaniza calabresa picante."),
            MenuLomiteria(nombre="Pizza Fugazzeta", precio=10500,
                          descripcion="Masa media, mucha cebolla, queso muzzarella y oliva."),
            MenuLomiteria(nombre="Pizza Napolitana", precio=11200,
                          descripcion="Muzzarella, rodajas de tomate fresco, ajo y perejil."),

            # --- EMPANADAS ---
            MenuLomiteria(nombre="Empanada Carne Suave", precio=1300,
                          descripcion="Carne molida especial, cebolla, huevo y aceituna."),
            MenuLomiteria(nombre="Empanada Carne Picante", precio=1300,
                          descripcion="Cortada a cuchillo, con ají molido y pimentón de la vera."),
            MenuLomiteria(nombre="Empanada Jamón y Queso", precio=1300, descripcion="Clásica de jamón y muzzarella."),
            MenuLomiteria(nombre="Empanada Pollo", precio=1300,
                          descripcion="Pollo desmenuzado con salsa blanca y verdeo."),
            MenuLomiteria(nombre="Empanada Árabe", precio=1300,
                          descripcion="Carne macerada en limón, cebolla y tomate."),

            # Packs Empanadas
            MenuLomiteria(nombre="Docena de Empanadas", precio=13000,
                          descripcion="12 unidades a elección (Ahorrás $2600)."),
            MenuLomiteria(nombre="Media Docena Empanadas", precio=7000, descripcion="6 unidades a elección."),

            # --- BEBIDAS ---
            MenuLomiteria(nombre="Coca Cola 1.5L", precio=3800, descripcion="Botella descartable."),
            MenuLomiteria(nombre="Sprite 1.5L", precio=3800, descripcion="Botella descartable."),
            MenuLomiteria(nombre="Agua Sin Gas 1.5L", precio=2500, descripcion="Botella grande."),
            MenuLomiteria(nombre="Cerveza Andes Rubia 1L", precio=4800, descripcion="Retornable."),
            MenuLomiteria(nombre="Cerveza Andes Roja 1L", precio=4800, descripcion="Retornable."),
            MenuLomiteria(nombre="Lata Coca Cola 354ml", precio=1800, descripcion="Lata fría."),

            # --- POSTRES ---
            MenuLomiteria(nombre="Helado 1KG", precio=8500,
                          descripcion="4 gustos a elección (Vainilla, Chocolate, Dulce de Leche, Frutilla)."),
            MenuLomiteria(nombre="Flan Casero", precio=2500, descripcion="Con dulce de leche o crema."),

            # --- PROMOCIONES ---
            MenuLomiteria(nombre="Promo Pareja", precio=28000,
                          descripcion="2 Lomos Completos + 1 Coca 1.5L + Papas Extra."),
            MenuLomiteria(nombre="Promo Pizza Party", precio=19500,
                          descripcion="1 Pizza Especial + 1 Pizza Muzza + 1 Cerveza 1L."),
            MenuLomiteria(nombre="Promo Mundial", precio=18000,
                          descripcion="2 Hamburguesas Americanas + 2 Latas de Cerveza.")
        ]

        db.add_all(menu_items)
        db.commit()
        print(f"✅ {len(menu_items)} productos cargados.")

        # ==========================================
        # 2. CARGA DE CLIENTES
        # ==========================================
        print("👥 Creando Clientes...")

        # Clientes Lomitería
        clientes_lomi = [
            ClienteLomiteria(ig_id="1001", nombre="Juan Perez", telefono="351111111", direccion="Av. Colon 1000"),
            ClienteLomiteria(ig_id="1002", nombre="Maria Garcia", telefono="351222222", direccion="Chacabuco 500, 3A"),
            ClienteLomiteria(ig_id="1003", nombre="Pedro Gomez", telefono="351333333", direccion="Estrada 120"),
        ]
        db.add_all(clientes_lomi)

        # Clientes Barbería
        clientes_barber = [
            ClienteBarberia(ig_id="2001", nombre="Carlos Tevez", telefono="351444444"),
            ClienteBarberia(ig_id="2002", nombre="Lionel Messi", telefono="351555555"),
            ClienteBarberia(ig_id="2003", nombre="Dibu Martinez", telefono="351666666"),
        ]
        db.add_all(clientes_barber)
        db.commit()

        # ==========================================
        # 3. HISTORIAL DE PEDIDOS (LOMITERÍA)
        # ==========================================
        print("🛒 Generando Historial de Pedidos...")

        # Recuperamos productos clave
        lomo = db.query(MenuLomiteria).filter_by(nombre="Lomo Completo").first()
        pizza = db.query(MenuLomiteria).filter_by(nombre="Pizza Muzzarella").first()
        coca = db.query(MenuLomiteria).filter_by(nombre="Coca Cola 1.5L").first()

        # Pedido 1: Entregado (Hace 1 semana)
        p1 = PedidoLomiteria(
            cliente_id=clientes_lomi[0].id,
            estado="entregado",
            total=lomo.precio + coca.precio,
            fecha=datetime.now() - timedelta(days=7),
            mp_payment_link="link_pagado"
        )
        db.add(p1)
        db.commit()
        db.add_all([
            ItemPedidoLomiteria(pedido_id=p1.id, producto_id=lomo.id, cantidad=1, precio_unitario=lomo.precio,
                                aclaraciones="Sin mayonesa"),
            ItemPedidoLomiteria(pedido_id=p1.id, producto_id=coca.id, cantidad=1, precio_unitario=coca.precio)
        ])

        # Pedido 2: Carrito Abierto (Actual)
        p2 = PedidoLomiteria(
            cliente_id=clientes_lomi[1].id,
            estado="carrito",
            total=pizza.precio * 2,
            fecha=datetime.now()
        )
        db.add(p2)
        db.commit()
        db.add(ItemPedidoLomiteria(pedido_id=p2.id, producto_id=pizza.id, cantidad=2, precio_unitario=pizza.precio))

        # Pedido 3: Cancelado (Ayer)
        p3 = PedidoLomiteria(
            cliente_id=clientes_lomi[2].id,
            estado="cancelado",
            total=lomo.precio,
            fecha=datetime.now() - timedelta(days=1)
        )
        db.add(p3)
        db.commit()

        # ==========================================
        # 4. HISTORIAL Y AGENDA (BARBERÍA)
        # ==========================================
        print("💈 Generando Agenda de Barbería...")

        turnos = [
            # Pasado (Historial)
            TurnoBarberia(
                cliente_id=clientes_barber[0].id,
                fecha_hora=datetime.now() - timedelta(days=10, hours=2),
                estado="completado",
                google_event_id="evt_old_1",
                nota="Corte clásico"
            ),
            # Futuro (Mañana 10:00)
            TurnoBarberia(
                cliente_id=clientes_barber[1].id,
                fecha_hora=datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1),
                estado="activo",
                google_event_id="evt_future_1",
                nota="Barba y Pelo"
            ),
            # Futuro (Pasado mañana 16:00)
            TurnoBarberia(
                cliente_id=clientes_barber[2].id,
                fecha_hora=datetime.now().replace(hour=16, minute=0, second=0, microsecond=0) + timedelta(days=2),
                estado="activo",
                google_event_id="evt_future_2",
                nota="Degradé"
            )
        ]
        db.add_all(turnos)
        db.commit()

        print("✨ BASE DE DATOS INICIALIZADA CORRECTAMENTE.")

    except Exception as e:
        print(f"❌ Error al inicializar DB: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()