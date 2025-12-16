from typing import Any, Dict, Optional, Union, List, Type
from sqlalchemy.orm import Session
from app.models.models import Client, Order, OrderItem, Product, Appointment, Professional, OrderStatus, Message
from sqlalchemy import desc

class CRUDBase:
    def __init__(self, model: Type):
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[Any]:
        """Obtiene un registro por su ID primario."""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_one(self, db: Session, **kwargs) -> Optional[Any]:
        """
        Busca UN registro que cumpla con los filtros.
        Uso: crud.client.get_one(db, instagram_id="123")
        Uso: crud.order.get_one(db, client_id=1, status="pending")
        """
        return db.query(self.model).filter_by(**kwargs).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100, **kwargs) -> List[Any]:
        """
        Retorna una LISTA de registros que cumplan los filtros.
        Uso: crud.professional.get_multi(db, type="optico")
        """
        return db.query(self.model).filter_by(**kwargs).offset(skip).limit(limit).all()

    def create(self, db: Session, **kwargs) -> Any:
        """
        Crea un registro directo con los argumentos pasados.
        Uso: crud.client.create(db, instagram_id="123", name="Pepe")
        """
        db_obj = self.model(**kwargs)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Any, **kwargs) -> Any:
        """
        Actualiza los campos de un objeto existente.
        Uso: crud.order.update(db, orden_obj, status="paid")
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


# --- CLASES EXTENDIDAS (Solo para lógica que NO es CRUD básico) ---

class CRUDProduct(CRUDBase):
    def search_fuzzy(self, db: Session, query_str: str) -> List[Product]:
        """
        Esta lógica no puede heredarse porque usa 'ilike' (LIKE %...%)
        en lugar de igualdad exacta.
        """
        return db.query(self.model).filter(self.model.name.ilike(f"%{query_str}%")).all()


class CRUDOrder(CRUDBase):
    def add_item(self, db: Session, order: Order, product: Product, quantity: int) -> Order:
        """
        Lógica transaccional compleja: Crea un Item Y actualiza el total de la Orden.
        No se puede hacer con un create() simple.
        """
        # 1. Crear el item usando el modelo directamente
        item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=product.price  # Congelamos el precio histórico
        )
        db.add(item)

        # 2. Actualizar el total de la orden
        current_total = order.total_amount or 0.0
        order.total_amount = current_total + (product.price * quantity)

        db.commit()
        db.refresh(order)
        return order

class CRUDProfessional(CRUDBase):
    def get_by_type_and_name(self, db: Session, type_prof: str, name_filter: str = None) -> List[Professional]:
        query = db.query(self.model).filter(self.model.type == type_prof)
        if name_filter:
            query = query.filter(self.model.name.ilike(f"%{name_filter}%"))
        return query.all()

class CRUDMessage(CRUDBase):
    def get_chat_history(self, db: Session, client_id: int, limit: int = 10):
        """Obtiene los últimos mensajes ordenados cronológicamente para la IA"""
        last_messages = db.query(self.model) \
            .filter(self.model.client_id == client_id) \
            .order_by(desc(self.model.id)) \
            .limit(limit) \
            .all()
        # Invertimos para que queden antiguo -> nuevo
        return last_messages[::-1]

professional = CRUDProfessional(Professional)
product = CRUDProduct(Product)
order = CRUDOrder(Order)
client = CRUDBase(Client)
message = CRUDMessage(Message)