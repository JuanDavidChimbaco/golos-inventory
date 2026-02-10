"""
Views para dashboard y estadísticas
"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema
from ..models import (
    ProductVariant, MovementInventory, Sale, Supplier, 
    Product
)
from ..core.services import low_stock_variants


class DashboardViewSet(viewsets.GenericViewSet):
    """
    ViewSet para dashboard y estadísticas del sistema
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(tags=['Dashboard'])
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Vista general del dashboard"""
        today = timezone.now().date()
        last_month = today - timedelta(days=30)
        last_week = today - timedelta(days=7)
        
        # Estadísticas de productos
        total_products = Product.objects.count()
        active_variants = ProductVariant.objects.filter(active=True).count()
        low_stock_count = low_stock_variants().count()
        
        # Estadísticas de ventas
        total_sales = Sale.objects.count()
        completed_sales = Sale.objects.filter(status='completed').count()
        pending_sales = Sale.objects.filter(status='pending').count()
        
        # Ventas del último mes
        recent_sales = Sale.objects.filter(created_at__gte=last_month)
        recent_sales_count = recent_sales.count()
        recent_sales_total = recent_sales.aggregate(
            total=Coalesce(Sum('total'), 0, output_field=DecimalField())
        )['total'] or 0
        
        # Ventas de la última semana
        weekly_sales = Sale.objects.filter(created_at__gte=last_week)
        weekly_sales_count = weekly_sales.count()
        weekly_sales_total = weekly_sales.aggregate(
            total=Coalesce(Sum('total'), 0, output_field=DecimalField())
        )['total'] or 0
        
        # Estadísticas de compras
        purchases = MovementInventory.objects.filter(
            movement_type=MovementInventory.MovementType.PURCHASE,
            created_at__gte=last_month
        )
        purchases_count = purchases.count()
        purchases_total_quantity = purchases.aggregate(
            total=Coalesce(Sum('quantity'), 0, output_field=DecimalField())
        )['total'] or 0
        
        # Estadísticas de proveedores
        total_suppliers = Supplier.objects.count()
        active_suppliers = Supplier.objects.filter(is_active=True).count()
        suppliers_with_purchases = Supplier.objects.filter(
            movements__movement_type=MovementInventory.MovementType.PURCHASE
        ).distinct().count()
        
        # Valor del inventario
        variants_with_stock = ProductVariant.objects.annotate(
            stock=Coalesce(Sum('movements__quantity'), 0, output_field=DecimalField())
        ).filter(stock__gt=0)
        
        inventory_value = sum(
            variant.stock * variant.cost for variant in variants_with_stock
        )
        
        return Response({
            'products': {
                'total': total_products,
                'active_variants': active_variants,
                'low_stock': low_stock_count,
                'inventory_value': inventory_value
            },
            'sales': {
                'total': total_sales,
                'completed': completed_sales,
                'pending': pending_sales,
                'recent_month': {
                    'count': recent_sales_count,
                    'total': recent_sales_total
                },
                'recent_week': {
                    'count': weekly_sales_count,
                    'total': weekly_sales_total
                }
            },
            'purchases': {
                'recent_month': {
                    'count': purchases_count,
                    'total_quantity': purchases_total_quantity
                }
            },
            'suppliers': {
                'total': total_suppliers,
                'active': active_suppliers,
                'with_purchases': suppliers_with_purchases
            }
        })
    
    @extend_schema(tags=['Dashboard'])
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Productos con stock bajo"""
        threshold = request.query_params.get('threshold', 10)
        
        try:
            threshold = int(threshold)
        except ValueError:
            threshold = 10
        
        low_stock = low_stock_variants()
        
        # Filtrar por umbral si se proporciona
        if threshold > 0:
            low_stock = low_stock.annotate(
                current_stock=Coalesce(Sum('movements__quantity'), 0, output_field=DecimalField())
            ).filter(current_stock__lte=threshold)
        
        data = []
        for variant in low_stock:
            current_stock = variant.current_stock
            data.append({
                'id': variant.id,
                'product_name': variant.product.name,
                'brand': variant.product.brand,
                'variant_info': f"{variant.get_gender_display()} - {variant.color} - {variant.size}",
                'current_stock': current_stock,
                'stock_minimum': variant.stock_minimum,
                'deficit': max(0, variant.stock_minimum - current_stock),
                'price': variant.price,
                'cost': variant.cost
            })
        
        return Response({
            'count': len(data),
            'threshold': threshold,
            'products': data
        })
    
    @extend_schema(tags=['Dashboard'])
    @action(detail=False, methods=['get'])
    def recent_movements(self, request):
        """Movimientos recientes de inventario"""
        limit = request.query_params.get('limit', 20)
        
        try:
            limit = int(limit)
            if limit > 100:
                limit = 100
        except ValueError:
            limit = 20
        
        movements = MovementInventory.objects.select_related(
            'variant', 'variant__product', 'supplier'
        ).order_by('-created_at')[:limit]
        
        data = []
        for movement in movements:
            data.append({
                'id': movement.id,
                'type': movement.movement_type,
                'type_display': movement.get_movement_type_display(),
                'product_name': movement.variant.product.name,
                'variant_info': f"{movement.variant.get_gender_display()} - {movement.variant.color} - {movement.variant.size}",
                'quantity': movement.quantity,
                'supplier': movement.supplier.name if movement.supplier else None,
                'observation': movement.observation,
                'created_at': movement.created_at,
                'created_by': movement.created_by
            })
        
        return Response({
            'count': len(data),
            'movements': data
        })
    
    @extend_schema(tags=['Dashboard'])
    @action(detail=False, methods=['get'])
    def sales_chart(self, request):
        """Datos para gráfico de ventas"""
        days = request.query_params.get('days', 30)
        
        try:
            days = int(days)
            if days > 365:
                days = 365
        except ValueError:
            days = 30
        
        start_date = timezone.now().date() - timedelta(days=days)
        
        # Ventas diarias
        sales_data = Sale.objects.filter(
            created_at__date__gte=start_date
        ).extra({
            'day': 'date(created_at)'
        }).values('day').annotate(
            count=Count('id'),
            total=Coalesce(Sum('total'), 0, output_field=DecimalField())
        ).order_by('day')
        
        # Compras diarias
        purchases_data = MovementInventory.objects.filter(
            movement_type=MovementInventory.MovementType.PURCHASE,
            created_at__date__gte=start_date
        ).extra({
            'day': 'date(created_at)'
        }).values('day').annotate(
            count=Count('id'),
            total_quantity=Coalesce(Sum('quantity'), 0, output_field=DecimalField())
        ).order_by('day')
        
        return Response({
            'sales': list(sales_data),
            'purchases': list(purchases_data),
            'period': {
                'start_date': start_date,
                'end_date': timezone.now().date(),
                'days': days
            }
        })
    
    @extend_schema(tags=['Dashboard'])
    @action(detail=False, methods=['get'])
    def top_products(self, request):
        """Productos más vendidos"""
        period = request.query_params.get('period', 'month')
        
        if period == 'week':
            start_date = timezone.now().date() - timedelta(days=7)
        elif period == 'year':
            start_date = timezone.now().date() - timedelta(days=365)
        else:  # month
            start_date = timezone.now().date() - timedelta(days=30)
        
        # Productos más vendidos por cantidad
        top_products = MovementInventory.objects.filter(
            movement_type=MovementInventory.MovementType.SALE_OUT,
            created_at__date__gte=start_date
        ).values(
            'variant__product__name', 'variant__product__brand'
        ).annotate(
            total_quantity=Coalesce(Sum('quantity'), 0, output_field=DecimalField()),
            sales_count=Count('id')
        ).order_by('-total_quantity')[:10]
        
        # Productos con mayor ingreso
        top_revenue = SaleDetail.objects.filter(
            sale__created_at__date__gte=start_date,
            sale__status='completed'
        ).values(
            'variant__product__name', 'variant__product__brand'
        ).annotate(
            total_revenue=Coalesce(Sum('subtotal'), 0, output_field=DecimalField()),
            total_quantity=Coalesce(Sum('quantity'), 0, output_field=DecimalField())
        ).order_by('-total_revenue')[:10]
        
        return Response({
            'by_quantity': list(top_products),
            'by_revenue': list(top_revenue),
            'period': period
        })
    
    @extend_schema(tags=['Dashboard'])
    @action(detail=False, methods=['get'])
    def supplier_performance(self, request):
        """Rendimiento de proveedores"""
        days = request.query_params.get('days', 90)
        
        try:
            days = int(days)
            if days > 365:
                days = 365
        except ValueError:
            days = 90
        
        start_date = timezone.now().date() - timedelta(days=days)
        
        suppliers_data = Supplier.objects.filter(
            movements__movement_type=MovementInventory.MovementType.PURCHASE,
            movements__created_at__date__gte=start_date
        ).annotate(
            total_purchases=Count('movements'),
            total_quantity=Coalesce(Sum('movements__quantity'), 0, output_field=DecimalField()),
            total_products=Count('movements__variant', distinct=True),
            last_purchase=Max('movements__created_at')
        ).order_by('-total_quantity')[:20]
        
        data = []
        for supplier in suppliers_data:
            data.append({
                'id': supplier.id,
                'name': supplier.name,
                'nit': supplier.nit,
                'total_purchases': supplier.total_purchases,
                'total_quantity': supplier.total_quantity,
                'total_products': supplier.total_products,
                'last_purchase': supplier.last_purchase,
                'is_active': supplier.is_active
            })
        
        return Response({
            'count': len(data),
            'period': f'Últimos {days} días',
            'suppliers': data
        })
