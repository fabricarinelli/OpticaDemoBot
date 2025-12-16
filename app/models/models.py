from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


# ==========================================
# 1. MÓDULO BARBERÍA
# =========================================
class ClienteBarberia(Base):
    __tablename__ = 'barberia_clientes'

    id = Column(Integer, primary_key=True)
    ig_id = Column(String, unique=True, index=True)
    nombre = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    turnos = relationship("TurnoBarberia", back_populates="cliente")
    mensajes = relationship("MensajeBarberia", back_populates="cliente")


class TurnoBarberia(Base):
    __tablename__ = 'barberia_turnos'
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('barberia_clientes.id'))
    fecha_hora = Column(DateTime)
    fecha_generacion = Column(DateTime, default=func.now())
    nota = Column(String, nullable=True)
    google_event_id = Column(String, unique=True)
    estado = Column(String, default='activo')
    cliente = relationship("ClienteBarberia", back_populates="turnos")

class MensajeBarberia(Base):
    """Historial de chat específico para la Barbería"""
    __tablename__ = 'barberia_mensajes'

    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('barberia_clientes.id'))

    role = Column(String)  # 'user' o 'model'
    content = Column(Text)  # El mensaje en sí
    timestamp = Column(DateTime, default=func.now())  # Fecha y hora automática

    cliente = relationship("ClienteBarberia", back_populates="mensajes")


# ==========================================
# 2. MÓDULO LOMITERÍA
# ==========================================

class ClienteLomiteria(Base):
    __tablename__ = 'lomiteria_clientes'
    id = Column(Integer, primary_key=True)
    ig_id = Column(String, unique=True, index=True)
    nombre = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    pedidos = relationship("PedidoLomiteria", back_populates="cliente")
    mensajes = relationship("MensajeLomiteria", back_populates="cliente")


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


class MensajeLomiteria(Base):
    """Historial de chat específico para la Lomitería"""
    __tablename__ = 'lomiteria_mensajes'
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('lomiteria_clientes.id'))
    role = Column(String)  # 'user' o 'model'
    content = Column(Text)
    timestamp = Column(DateTime, default=func.now())
    cliente = relationship("ClienteLomiteria", back_populates="mensajes")