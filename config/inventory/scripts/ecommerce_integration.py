"""
Integración para E-Commerce
Gestión de clientes y pedidos desde tienda online
"""

from django.contrib.auth.models import User, Group
from inventory.models import Product, Sale, SaleDetail, ProductVariant
from decimal import Decimal

class ECommerceCustomer:
    """Clase para gestionar clientes de e-commerce"""
    
    @staticmethod
    def create_customer(username, email, password, first_name="", last_name=""):
        """
        Crea un nuevo cliente de e-commerce
        
        Args:
            username: Nombre de usuario único
            email: Email del cliente
            password: Contraseña
            first_name: Nombre (opcional)
            last_name: Apellido (opcional)
            
        Returns:
            User: Usuario creado con permisos de cliente
        """
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Asignar al grupo Customers
        customers_group = Group.objects.get(name='Customers')
        user.groups.add(customers_group)
        
        # No es staff (no puede acceder a admin)
        user.is_staff = False
        user.save()
        
        return user
    
    @staticmethod
    def create_order(customer_username, items_data):
        """
        Crea un pedido desde el e-commerce
        
        Args:
            customer_username: Username del cliente
            items_data: Lista de items [
                {'variant_id': 1, 'quantity': 2, 'price': 10.50},
                {'variant_id': 3, 'quantity': 1, 'price': 25.00}
            ]
            
        Returns:
            Sale: Pedido creado
        """
        try:
            customer = User.objects.get(username=customer_username)
            
            # Verificar que sea cliente
            if not customer.groups.filter(name='Customers').exists():
                raise ValueError("Usuario no es un cliente válido")
            
            # Crear la venta
            sale = Sale.objects.create(
                customer=f"{customer.first_name} {customer.last_name}".strip() or customer.username,
                created_by=customer.username,
                status="pending",
                total=Decimal('0.00')
            )
            
            # Agregar detalles
            total = Decimal('0.00')
            for item in items_data:
                variant = ProductVariant.objects.get(id=item['variant_id'])
                
                # Verificar stock
                if variant.stock < item['quantity']:
                    raise ValueError(f"Stock insuficiente para {variant.product.name}")
                
                # Crear detalle
                SaleDetail.objects.create(
                    sale=sale,
                    variant=variant,
                    quantity=item['quantity'],
                    unit_price=Decimal(str(item['price']))
                )
                
                total += Decimal(str(item['price'])) * item['quantity']
            
            # Actualizar total
            sale.total = total
            sale.save()
            
            return sale
            
        except User.DoesNotExist:
            raise ValueError("Cliente no encontrado")
        except ProductVariant.DoesNotExist:
            raise ValueError("Variante de producto no encontrada")
    
    @staticmethod
    def get_customer_orders(customer_username):
        """
        Obtiene todos los pedidos de un cliente
        
        Args:
            customer_username: Username del cliente
            
        Returns:
            QuerySet: Pedidos del cliente
        """
        try:
            customer = User.objects.get(username=customer_username)
            return Sale.objects.filter(created_by=customer.username)
        except User.DoesNotExist:
            raise ValueError("Cliente no encontrado")
    
    @staticmethod
    def check_product_stock(variant_id):
        """
        Verifica stock disponible de un producto
        
        Args:
            variant_id: ID de la variante
            
        Returns:
            dict: Información de stock
        """
        try:
            variant = ProductVariant.objects.get(id=variant_id)
            return {
                'variant_id': variant.id,
                'product_name': variant.product.name,
                'variant_info': f"{variant.product.name} - {variant.gender} - {variant.size}",
                'stock_available': variant.stock,
                'is_available': variant.stock > 0
            }
        except ProductVariant.DoesNotExist:
            raise ValueError("Variante no encontrada")


# Ejemplos de uso
if __name__ == "__main__":
    # Crear cliente
    customer = ECommerceCustomer.create_customer(
        username="juan_cliente",
        email="juan@tienda.com",
        password="cliente123",
        first_name="Juan",
        last_name="Pérez"
    )
    print(f"✅ Cliente creado: {customer.username}")
    
    # Crear pedido
    try:
        order = ECommerceCustomer.create_order(
            customer_username="juan_cliente",
            items_data=[
                {'variant_id': 1, 'quantity': 2, 'price': 10.50},
                {'variant_id': 2, 'quantity': 1, 'price': 25.00}
            ]
        )
        print(f"✅ Pedido creado: #{order.id} - Total: ${order.total}")
    except ValueError as e:
        print(f"❌ Error al crear pedido: {e}")
    
    # Ver pedidos del cliente
    orders = ECommerceCustomer.get_customer_orders("juan_cliente")
    print(f"📋 Pedidos de Juan: {orders.count()} pedidos")
    
    # Ver stock
    stock_info = ECommerceCustomer.check_product_stock(1)
    print(f"📦 Stock disponible: {stock_info['stock_available']} unidades")
