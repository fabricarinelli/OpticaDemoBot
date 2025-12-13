from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from sqlalchemy.sql.sqltypes import Text

from app.core.database import Base

# Enums para consistencia
class ProfessionalType(str, enum.Enum):
    OPTICO = "optico"
    CONTACTOLOGO = "contactologo"

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    instagram_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True) # Lo podemos sacar del perfil de IG
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relación con los mensajes
    messages = relationship("Message", back_populates="client")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    role = Column(String) # "user" o "assistant"
    content = Column(Text) # El texto del mensaje
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="messages")

class Professional(Base):
    __tablename__ = "professionals"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(Enum(ProfessionalType))
    calendar_id = Column(String, unique=True, nullable=False)
    appointments = relationship("Appointment", back_populates="professional")

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    professional_id = Column(Integer, ForeignKey("professionals.id"))
    
    start_time = Column(DateTime, index=True)
    calendar_event_id = Column(String, nullable=True)
    status = Column(String, default="confirmed") 
    
    client = relationship("Client", back_populates="appointments")
    
    # --- CORRECCIÓN AQUÍ ABAJO ---
    # Antes decía back_populates="professional", ahora apunta a la LISTA "appointments"
    professional = relationship("Professional", back_populates="appointments")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    description = Column(String)
    price = Column(Float)
    category = Column(String)

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    total_amount = Column(Float, default=0.0)
    payment_link = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    client = relationship("Client", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)
    unit_price = Column(Float)
    
    order = relationship("Order", back_populates="items")
    product = relationship("Product")
