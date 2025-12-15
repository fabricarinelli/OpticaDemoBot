# app/scripts/init_db.py
from app.core.database import Base, engine, SessionLocal
from app.models.models import Professional, Product, ProfessionalType

# 1. Crear Tablas (si no existen)
print("Creando tablas en la base de datos...")
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# --- PROFESIONALES ---
# Verificamos si ya existen profesionales para no duplicarlos
if not db.query(Professional).first():
    print("Insertando Profesionales...")

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

    db.add_all([p1, p2, p3, p4])
    db.commit()
    print("✅ Profesionales insertados.")
else:
    print("ℹ️ Los profesionales ya estaban cargados.")

# --- PRODUCTOS ---
# Si hay pocos productos (menos de 5), asumimos que falta el catálogo completo y lo cargamos.
if db.query(Product).count() < 5:
    print("Insertando Catálogo Extendido de Productos...")

    products_list = [
        # --- LÍQUIDOS Y SOLUCIONES ---
        Product(name="Liquido Renu 500ml", price=15000, category="liquidos",
                description="Solución multipropósito para lentes blandas"),
        Product(name="Liquido Opti-Free Express 355ml", price=18500, category="liquidos",
                description="Desinfección prolongada Alcon"),
        Product(name="Biotrue 300ml", price=22000, category="liquidos",
                description="Inspirado en la biología de tus ojos"),
        Product(name="Solución Salina 500ml", price=8000, category="liquidos",
                description="Para enjuague de lentes de contacto"),

        # --- ANTEOJOS DE SOL ---
        Product(name="RayBan Aviator Classic", price=180000, category="anteojos_sol",
                description="G-15 Lens, Marco Dorado"),
        Product(name="RayBan Wayfarer", price=175000, category="anteojos_sol", description="Negro Clásico, Polarizado"),
        Product(name="Oakley Holbrook", price=210000, category="anteojos_sol",
                description="Matte Black, Prizm Sapphire"),
        Product(name="Vulk The Guardian", price=120000, category="anteojos_sol",
                description="Estilo urbano, protección UV400"),
        Product(name="Rusty Vicio", price=95000, category="anteojos_sol", description="Diseño envolvente deportivo"),

        # --- ARMAZONES RECETA ---
        Product(name="Armazón Vulk Harry", price=85000, category="armazones",
                description="Acetato negro, formato redondo"),
        Product(name="Armazón Reef Titanio", price=110000, category="armazones",
                description="Ultraliviano, rectangular"),
        Product(name="Armazón Infinit Love", price=92000, category="armazones",
                description="Cat-eye moderno, varios colores"),

        # --- LENTES DE CONTACTO (Cajas) ---
        Product(name="Acuvue Oasys (Caja x6)", price=65000, category="lentes_contacto",
                description="Reemplazo quincenal, con Hydraclear"),
        Product(name="Air Optix HydraGlyde (Caja x6)", price=68000, category="lentes_contacto",
                description="Reemplazo mensual, alta oxigenación"),
        Product(name="Dailies Total 1 (Caja x30)", price=95000, category="lentes_contacto",
                description="Descartables diarios, comodidad superior"),

        # --- ACCESORIOS ---
        Product(name="Estuche Rígido Premium", price=8500, category="accesorios",
                description="Interior afelpado, cierre magnético"),
        Product(name="Gamuza Microfibra Grande", price=3000, category="accesorios",
                description="Limpieza sin rayas 20x20cm"),
        Product(name="Spray Limpiador y Antiempañante", price=6500, category="accesorios",
                description="Spray 30ml para cristales"),
        Product(name="Cadena Sujetadora Metal", price=4500, category="accesorios",
                description="Cadena fina dorada o plateada"),
    ]

    db.add_all(products_list)
    db.commit()
    print("✅ ¡Catálogo de productos cargado exitosamente!")
else:
    print("ℹ️ El catálogo de productos ya contiene datos.")

db.close()