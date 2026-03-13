"""
Management command to seed the database with 10 test products,
variants, and inventory movements for local development.
"""
import random
from django.core.management.base import BaseCommand
from inventory.models import Product, ProductVariant, MovementInventory, Supplier


PRODUCTS_DATA = [
    {
        "name": "YEEZY BOOST 350 V2",
        "brand": "Adidas",
        "description": "Zapatilla icónica con diseño Primeknit y suela Boost. Comodidad extrema para el día a día con un estilo urbano inconfundible.",
        "product_type": "sneakers",
        "variants": [
            {"size": "38", "color": "Beluga", "gender": "unisex", "price": 850000, "cost": 520000},
            {"size": "40", "color": "Beluga", "gender": "unisex", "price": 850000, "cost": 520000},
            {"size": "42", "color": "Zebra", "gender": "unisex", "price": 890000, "cost": 550000},
            {"size": "44", "color": "Zebra", "gender": "unisex", "price": 890000, "cost": 550000},
        ],
    },
    {
        "name": "AIR JORDAN 1 RETRO HIGH",
        "brand": "Nike",
        "description": "El clásico que definió la cultura sneaker. Cuero premium con el swoosh icónico y la silueta high-top que nunca pasa de moda.",
        "product_type": "sneakers",
        "variants": [
            {"size": "39", "color": "Chicago", "gender": "male", "price": 920000, "cost": 600000},
            {"size": "41", "color": "Chicago", "gender": "male", "price": 920000, "cost": 600000},
            {"size": "43", "color": "Royal Blue", "gender": "male", "price": 900000, "cost": 580000},
            {"size": "38", "color": "UNC", "gender": "female", "price": 900000, "cost": 580000},
        ],
    },
    {
        "name": "FORUM LOW",
        "brand": "Adidas",
        "description": "Diseño retro-basketball de los 80s con correa en el tobillo. Silueta limpia y versátil, perfecta para cualquier outfit casual.",
        "product_type": "sneakers",
        "variants": [
            {"size": "37", "color": "Blanco/Azul", "gender": "unisex", "price": 420000, "cost": 250000},
            {"size": "39", "color": "Blanco/Azul", "gender": "unisex", "price": 420000, "cost": 250000},
            {"size": "41", "color": "Blanco/Verde", "gender": "unisex", "price": 420000, "cost": 250000},
        ],
    },
    {
        "name": "CLASSIC LEATHER",
        "brand": "Reebok",
        "description": "Silueta atemporal en cuero suave con suela ligera. El zapato clásico que combina con todo, para los que prefieren lo simple y elegante.",
        "product_type": "classics",
        "variants": [
            {"size": "38", "color": "Blanco", "gender": "unisex", "price": 350000, "cost": 200000},
            {"size": "40", "color": "Blanco", "gender": "unisex", "price": 350000, "cost": 200000},
            {"size": "42", "color": "Negro", "gender": "male", "price": 350000, "cost": 200000},
        ],
    },
    {
        "name": "CHUCK TAYLOR ALL STAR",
        "brand": "Converse",
        "description": "El ícono que trascendió generaciones. Canvas resistente, suela de caucho vulcanizado y el parche de estrella que todos reconocen.",
        "product_type": "classics",
        "variants": [
            {"size": "36", "color": "Negro", "gender": "unisex", "price": 280000, "cost": 150000},
            {"size": "38", "color": "Negro", "gender": "unisex", "price": 280000, "cost": 150000},
            {"size": "40", "color": "Rojo", "gender": "unisex", "price": 280000, "cost": 150000},
            {"size": "42", "color": "Blanco", "gender": "unisex", "price": 280000, "cost": 150000},
            {"size": "44", "color": "Blanco", "gender": "male", "price": 280000, "cost": 150000},
        ],
    },
    {
        "name": "DR. MARTENS 1460",
        "brand": "Dr. Martens",
        "description": "Bota de 8 ojales con suela de aire AirWair. Cuero liso Smooth con la costura amarilla característica. Resistente y con actitud.",
        "product_type": "boots",
        "variants": [
            {"size": "37", "color": "Negro", "gender": "female", "price": 750000, "cost": 480000},
            {"size": "39", "color": "Negro", "gender": "unisex", "price": 750000, "cost": 480000},
            {"size": "41", "color": "Cherry Red", "gender": "unisex", "price": 780000, "cost": 500000},
        ],
    },
    {
        "name": "BIRKENSTOCK ARIZONA",
        "brand": "Birkenstock",
        "description": "Sandalia de dos correas con plantilla de corcho-látex anatómica. La comodidad alemana que se volvió tendencia global.",
        "product_type": "sandals",
        "variants": [
            {"size": "36", "color": "Marrón", "gender": "female", "price": 480000, "cost": 300000},
            {"size": "38", "color": "Marrón", "gender": "female", "price": 480000, "cost": 300000},
            {"size": "40", "color": "Negro", "gender": "unisex", "price": 480000, "cost": 300000},
            {"size": "42", "color": "Negro", "gender": "male", "price": 480000, "cost": 300000},
        ],
    },
    {
        "name": "PUMA SUEDE CLASSIC",
        "brand": "Puma",
        "description": "La zapatilla de ante que pasó de las canchas a la calle. Formstrip lateral icónico y silueta retro que no falla.",
        "product_type": "sneakers",
        "variants": [
            {"size": "38", "color": "Azul/Blanco", "gender": "unisex", "price": 380000, "cost": 220000},
            {"size": "40", "color": "Azul/Blanco", "gender": "unisex", "price": 380000, "cost": 220000},
            {"size": "42", "color": "Rojo/Blanco", "gender": "male", "price": 380000, "cost": 220000},
        ],
    },
    {
        "name": "NEW BALANCE 550",
        "brand": "New Balance",
        "description": "Silueta basketball retro de los 80s que resurgió como fenómeno streetwear. Cuero premium y detalles N prominentes.",
        "product_type": "sneakers",
        "variants": [
            {"size": "37", "color": "Blanco/Verde", "gender": "unisex", "price": 550000, "cost": 340000},
            {"size": "39", "color": "Blanco/Verde", "gender": "unisex", "price": 550000, "cost": 340000},
            {"size": "41", "color": "Blanco/Azul", "gender": "unisex", "price": 550000, "cost": 340000},
            {"size": "43", "color": "Blanco/Rojo", "gender": "male", "price": 550000, "cost": 340000},
        ],
    },
    {
        "name": "TIMBERLAND 6-INCH PREMIUM",
        "brand": "Timberland",
        "description": "La bota amarilla inconfundible. Cuero nubuck impermeabilizado, suela con agarre y construcción robusta para cualquier terreno.",
        "product_type": "boots",
        "variants": [
            {"size": "39", "color": "Wheat", "gender": "male", "price": 820000, "cost": 530000},
            {"size": "41", "color": "Wheat", "gender": "male", "price": 820000, "cost": 530000},
            {"size": "43", "color": "Negro", "gender": "male", "price": 820000, "cost": 530000},
            {"size": "37", "color": "Wheat", "gender": "female", "price": 780000, "cost": 500000},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed the database with 10 test products, variants, and stock for development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing products, variants, and movements before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            MovementInventory.objects.all().delete()
            ProductVariant.objects.all().delete()
            Product.objects.all().delete()
            self.stdout.write(self.style.WARNING("  ✓ Cleared all products, variants, and movements"))

        # Create a dev supplier
        supplier, _ = Supplier.objects.get_or_create(
            name="Proveedor Dev",
            defaults={
                "phone": "3001234567",
                "address": "Cali, Colombia",
                "is_active": True,
                "created_by": "seed_script",
            },
        )

        total_products = 0
        total_variants = 0
        total_movements = 0

        for product_data in PRODUCTS_DATA:
            variants_data = product_data.pop("variants")

            product, created = Product.objects.get_or_create(
                name=product_data["name"],
                brand=product_data["brand"],
                defaults={
                    **product_data,
                    "created_by": "seed_script",
                    "updated_by": "seed_script",
                },
            )

            if not created:
                self.stdout.write(f"  → {product.name} already exists, skipping...")
                continue

            total_products += 1
            self.stdout.write(f"  ✓ Created: {product.name} ({product.brand})")

            for v_data in variants_data:
                variant = ProductVariant.objects.create(
                    product=product,
                    size=v_data["size"],
                    color=v_data["color"],
                    gender=v_data["gender"],
                    price=v_data["price"],
                    cost=v_data["cost"],
                    stock_minimum=2,
                    active=True,
                    created_by="seed_script",
                    updated_by="seed_script",
                )

                # Add random stock (purchase movement)
                qty = random.randint(3, 15)
                MovementInventory.objects.create(
                    variant=variant,
                    movement_type="purchase",
                    quantity=qty,
                    observation=f"Stock inicial de prueba - seed script",
                    supplier=supplier,
                    created_by="seed_script",
                )

                total_variants += 1
                total_movements += 1
                self.stdout.write(
                    f"    • {variant.color} T{variant.size} ({variant.gender}) "
                    f"— ${variant.price:,.0f} — stock: {qty}"
                )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"✅ Seed complete: {total_products} products, "
            f"{total_variants} variants, {total_movements} movements"
        ))
