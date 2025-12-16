from typing import Any, List, Optional, Type
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.models import (
    ClienteBarberia, TurnoBarberia, MensajeBarberia,
    ClienteLomiteria, MenuLomiteria, PedidoLomiteria, ItemPedidoLomiteria, MensajeLomiteria)

class CRUDBase:
    def __init__(self, model: Type):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).
        **model**: A SQLAlchemy model class
        """
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[Any]:
        """Obtiene un registro por su ID primario."""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_one(self, db: Session, **kwargs) -> Optional[Any]:
        """
        Busca UN registro que cumpla con los filtros exactos pasados como kwargs.
        Uso: crud_cliente.get_one(db, ig_id="12345")
        """
        return db.query(self.model).filter_by(**kwargs).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100, **kwargs) -> List[Any]:
        """
        Retorna una LISTA de registros que cumplan los filtros.
        Uso: crud_turnos.get_multi(db, estado="activo", limit=5)
        """
        return db.query(self.model).filter_by(**kwargs).offset(skip).limit(limit).all()

    def create(self, db: Session, **kwargs) -> Any:
        """
        Crea un registro directo con los argumentos pasados.
        Uso: crud_cliente.create(db, nombre="Juan", telefono="123")
        """
        db_obj = self.model(**kwargs)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Any, **kwargs) -> Any:
        """
        Actualiza los campos de un objeto existente.
        Uso: crud_turno.update(db, turno_obj, estado="cancelado", nota="Cliente no vino")
        """
        for field, value in kwargs.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: int) -> Any:
        """Elimina un registro por ID."""
        obj = db.query(self.model).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj


# ==============================================================================
# 2. INSTANCIAS (SIN EXTENDER CLASES)
# ==============================================================================
# Aquí creamos los objetos listos para usar en el resto de la app.

# Barbería
cliente_barberia = CRUDBase(ClienteBarberia)
turno_barberia = CRUDBase(TurnoBarberia)
mensaje_barberia = CRUDBase(MensajeBarberia)

# Lomitería
cliente_lomiteria = CRUDBase(ClienteLomiteria)
menu_lomiteria = CRUDBase(MenuLomiteria)
pedido_lomiteria = CRUDBase(PedidoLomiteria)
item_pedido_lomiteria = CRUDBase(ItemPedidoLomiteria)
mensaje_lomiteria = CRUDBase(MensajeLomiteria)


# ==============================================================================
# 3. FUNCIONES ESPECIALES (Helper Functions)
# ==============================================================================
# Lógica que no entra en el CRUD genérico porque es muy específica.

def get_chat_history(db: Session, model_mensaje: Type, cliente_id: int, limit: int = 10) -> List[dict]:
    """
    Obtiene los últimos N mensajes formateados para Gemini.
    Funciona tanto para MensajeBarberia como MensajeLomiteria.
    """
    # 1. Traemos los últimos 10 (orden descendente por fecha)
    mensajes_desc = db.query(model_mensaje) \
        .filter_by(cliente_id=cliente_id) \
        .order_by(desc(model_mensaje.timestamp)) \
        .limit(limit) \
        .all()

    history = mensajes_desc[::-1]
    return history


def search_menu_fuzzy(db: Session, query: str) -> List[MenuLomiteria]:
    """
    Búsqueda 'fuzzy' (parcial) para el menú.
    'filtros=kwargs' busca igualdad exacta, esto busca 'parecido'.
    """
    return db.query(MenuLomiteria) \
        .filter(MenuLomiteria.nombre.ilike(f"%{query}%"), MenuLomiteria.activo == True) \
        .all()


def add_item_to_order(db: Session, pedido_obj: PedidoLomiteria, producto_obj: MenuLomiteria, cantidad: int = 1):
    """
    Lógica transaccional: Agrega item Y actualiza el total del pedido.
    """
    # 1. Crear Item
    item = ItemPedidoLomiteria(
        pedido_id=pedido_obj.id,
        producto_id=producto_obj.id,
        cantidad=cantidad,
        precio_unitario=producto_obj.precio,  # Congelamos precio
        aclaraciones=""
    )
    db.add(item)

    # 2. Actualizar Total del Pedido
    total_actual = pedido_obj.total or 0.0
    nuevo_total = total_actual + (producto_obj.precio * cantidad)

    # Usamos el crud genérico para actualizar el pedido
    pedido_lomiteria.update(db, pedido_obj, total=nuevo_total)

    return item