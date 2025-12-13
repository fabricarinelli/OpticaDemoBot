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

    p1 = Professional(
        name="Lic. Juan (Óptico)",
        type=ProfessionalType.OPTICO,
        calendar_id="3a87428b88c7324f9d88872da1dfe966f4cfd759e337b7eb765f4f97d146f1e0@group.calendar.google.com"
    )
    p2 = Professional(
        name="Lic. Daniela (Óptica)",
        type=ProfessionalType.OPTICO,
        calendar_id="4932e0a89f768d94c13eda80628ec690e04d4bbf21585eac15ec11be6a0edac2@group.calendar.google.com"
    )

    # Contactólogos (30 min)
    p3 = Professional(
        name="Dra. Malena (Contactóloga)",
        type=ProfessionalType.CONTACTOLOGO,
        calendar_id="80a63f7c91981f4b0a4e00944046aa27a3c4e232e1f32cc36358e70bdf4cecae@group.calendar.google.com"
    )
    p4 = Professional(
        name="Dr. Roberto (Contactólogo)",
        type=ProfessionalType.CONTACTOLOGO,
        calendar_id="01044e93d895c54a1f14a1a00f85b4518582a15ba09a7c16efcc1facd8d1b374@group.calendar.google.com"
    )

    # Productos (Según SRS RF-2.1)
    prod1 = Product(name="Liquido Renu 500ml", price=15000, category="liquidos", description="Solución multipropósito")
    prod2 = Product(name="Anteojos de Sol RayBan", price=120000, category="anteojos",
                    description="Modelo Aviador Clásico")
    prod3 = Product(name="Estuche Rígido", price=5000, category="accesorios", description="Protección para tus lentes")

    db.add_all([p1, p2, p3, p4, prod1, prod2, prod3])
    db.commit()
    print("¡Datos insertados correctamente!")
else:
    print("La base de datos ya tiene datos.")

db.close()