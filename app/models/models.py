from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class ClienteBarberia(Base):
    __tablename__ = 'barberia_clientes'

    id = Column(Integer, primary_key=True)
    ig_id = Column(String, unique=True, index=True)
    nombre = Column(String)
    telefono = Column(String)
    turnos = relationship("TurnoBarberia", back_populates="cliente")


class TurnoBarberia(Base):
    __tablename__ = 'barberia_turnos'
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('barberia_clientes.id'))
    fecha_hora = Column(DateTime)  # La fecha del turno (Ej: 2025-12-15 10:00:00)
    fecha_generacion = Column(DateTime, default=func.now())
    nota = Column(String, nullable=True)
    google_event_id = Column(String, unique=True)
    estado = Column(String, default='activo')
    cliente = relationship("ClienteBarberia", back_populates="turnos")


class ClienteLomiteria(Base):
    __tablename__ = 'lomiteria_clientes'

    id = Column(Integer, primary_key=True)
    ig_id = Column(String, unique=True, index=True)
    nombre = Column(String)
    telefono = Column(String)
    direccion = Column(String, nullable=True)  # Para envíos

    pedidos = relationship("PedidoLomiteria", back_populates="cliente")


class MenuLomiteria(Base):
    __tablename__ = 'lomiteria_menu'

    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    descripcion = Column(String)
    precio = Column(Float)
    activo = Column(Boolean, default=True)


class PedidoLomiteria(Base):
    __tablename__ = 'lomiteria_pedidos'

    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('lomiteria_clientes.id'))
    fecha = Column(DateTime, default=func.now())
    total = Column(Float, default=0.0)
    estado = Column(String, default='pendiente')
    mp_preference_id = Column(String, nullable=True)
    mp_payment_link = Column(String, nullable=True)
    cliente = relationship("ClienteLomiteria", back_populates="pedidos")
    items = relationship("ItemPedidoLomiteria", back_populates="pedido")

class ItemPedidoLomiteria(Base):
    __tablename__ = 'lomiteria_items_pedido'

    id = Column(Integer, primary_key=True)
    pedido_id = Column(Integer, ForeignKey('lomiteria_pedidos.id'))
    producto_id = Column(Integer, ForeignKey('lomiteria_menu.id'))
    cantidad = Column(Integer, default=1)
    precio_unitario = Column(Float)
    aclaraciones = Column(String, nullable=True)
    pedido = relationship("PedidoLomiteria", back_populates="items")
    producto = relationship("MenuLomiteria")