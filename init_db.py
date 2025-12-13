# init_db.py
from app.core.database import Base, engine, SessionLocal
from app.models.models import Professional, Product, ProfessionalType

# 1. Crear Tablas
print("Creando tablas en la base de datos...")
Base.metadata.create_all(bind=engine)

# 2. Datos de Prueba (Seed)
db = SessionLocal()

# Verificar si ya existen datos
if not db.query(Professional).first():
    print("Insertando datos de prueba...")

    # Profesionales (Según SRS RF-1.1)
    p1 = Professional(name="Lic. Juan Optico", type=ProfessionalType.OPTICO)
    p2 = Professional(name="Dra. Laura Contacto", type=ProfessionalType.CONTACTOLOGO)

    # Productos (Según SRS RF-2.1)
    prod1 = Product(name="Liquido Renu 500ml", price=15000, category="liquidos", description="Solución multipropósito")
    prod2 = Product(name="Anteojos de Sol RayBan", price=120000, category="anteojos",
                    description="Modelo Aviador Clásico")
    prod3 = Product(name="Estuche Rígido", price=5000, category="accesorios", description="Protección para tus lentes")

    db.add_all([p1, p2, prod1, prod2, prod3])
    db.commit()
    print("¡Datos insertados correctamente!")
else:
    print("La base de datos ya tiene datos.")

db.close()