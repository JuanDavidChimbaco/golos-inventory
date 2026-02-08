"""
Views para exportación de datos
"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
import pandas as pd
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
from drf_spectacular.utils import extend_schema
from ..models import (
    Sale, SaleDetail, MovementInventory, Supplier, 
    ProductVariant, Product
)


class ExportViewSet(viewsets.GenericViewSet):
    """
    ViewSet para exportación de datos
    """
    permission_classes = [permissions.IsAuthenticated]
    
    # Tags para documentación Swagger
    tags = ['Export']
    
    @extend_schema(tags=['Export'])
    @action(detail=False, methods=['get'])
    def sales(self, request):
        """Exportar ventas a CSV o Excel"""
        format_type = request.query_params.get('format', 'csv')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        status_filter = request.query_params.get('status')
        
        # Construir queryset
        queryset = Sale.objects.select_related('details__variant__product').all()
        
        # Aplicar filtros
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=end_date)
            except ValueError:
                pass
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Preparar datos
        data = []
        for sale in queryset:
            for detail in sale.details.all():
                data.append({
                    'ID Venta': sale.id,
                    'Cliente': sale.customer,
                    'Estado': sale.get_status_display(),
                    'Fecha': sale.created_at.strftime('%Y-%m-%d %H:%M'),
                    'Producto': detail.variant.product.name,
                    'Marca': detail.variant.product.brand,
                    'Variante': f"{detail.variant.get_gender_display()} - {detail.variant.color} - {detail.variant.size}",
                    'Cantidad': detail.quantity,
                    'Precio Unitario': float(detail.price),
                    'Subtotal': float(detail.subtotal),
                    'Total Venta': float(sale.total),
                    'Creado por': sale.created_by
                })
        
        # Crear DataFrame
        df = pd.DataFrame(data)
        
        if format_type.lower() == 'excel':
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="ventas_{timezone.now().strftime("%Y%m%d")}.xlsx"'
            df.to_excel(response, index=False, engine='openpyxl')
        else:  # CSV
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="ventas_{timezone.now().strftime("%Y%m%d")}.csv"'
            df.to_csv(response, index=False, encoding='utf-8-sig')
        
        return response
    
    @extend_schema(tags=['Export'])
    @action(detail=False, methods=['get'])
    def purchases(self, request):
        """Exportar compras a CSV o Excel"""
        format_type = request.query_params.get('format', 'csv')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        supplier_id = request.query_params.get('supplier')
        
        # Construir queryset
        queryset = MovementInventory.objects.filter(
            movement_type=MovementInventory.MovementType.PURCHASE
        ).select_related('variant__product', 'supplier')
        
        # Aplicar filtros
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=end_date)
            except ValueError:
                pass
        
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        
        # Preparar datos
        data = []
        for purchase in queryset:
            data.append({
                'ID Compra': purchase.id,
                'Proveedor': purchase.supplier.name if purchase.supplier else 'N/A',
                'NIT': purchase.supplier.nit if purchase.supplier else 'N/A',
                'Producto': purchase.variant.product.name,
                'Marca': purchase.variant.product.brand,
                'Variante': f"{purchase.variant.get_gender_display()} - {purchase.variant.color} - {purchase.variant.size}",
                'Cantidad': purchase.quantity,
                'Costo Unitario': float(purchase.variant.cost),
                'Total Compra': float(purchase.quantity * purchase.variant.cost),
                'Observación': purchase.observation or '',
                'Fecha': purchase.created_at.strftime('%Y-%m-%d %H:%M'),
                'Creado por': purchase.created_by
            })
        
        # Crear DataFrame
        df = pd.DataFrame(data)
        
        if format_type.lower() == 'excel':
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="compras_{timezone.now().strftime("%Y%m%d")}.xlsx"'
            df.to_excel(response, index=False, engine='openpyxl')
        else:  # CSV
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="compras_{timezone.now().strftime("%Y%m%d")}.csv"'
            df.to_csv(response, index=False, encoding='utf-8-sig')
        
        return response
    
    @extend_schema(tags=['Export'])
    @action(detail=False, methods=['get'])
    def inventory(self, request):
        """Exportar estado actual del inventario a CSV o Excel"""
        format_type = request.query_params.get('format', 'csv')
        include_zero_stock = request.query_params.get('include_zero', 'false').lower() == 'true'
        
        # Construir queryset con stock actual
        variants = ProductVariant.objects.select_related('product').annotate(
            stock_actual=Sum('movements__quantity')
        ).filter(active=True)
        
        if not include_zero_stock:
            variants = variants.filter(stock_actual__gt=0)
        
        # Preparar datos
        data = []
        for variant in variants:
            stock = variant.stock_actual or 0
            data.append({
                'Producto': variant.product.name,
                'Marca': variant.product.brand,
                'Variante': f"{variant.get_gender_display()} - {variant.color} - {variant.variant.size}",
                'Stock Actual': stock,
                'Stock Mínimo': variant.stock_minimum,
                'Precio Venta': float(variant.price),
                'Costo Unitario': float(variant.cost),
                'Valor Inventario': float(stock * variant.cost),
                'Estado': 'Activo' if variant.active else 'Inactivo',
                'Diferencia Stock': max(0, variant.stock_minimum - stock) if stock < variant.stock_minimum else 0
            })
        
        # Crear DataFrame
        df = pd.DataFrame(data)
        
        if format_type.lower() == 'excel':
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="inventario_{timezone.now().strftime("%Y%m%d")}.xlsx"'
            df.to_excel(response, index=False, engine='openpyxl')
        else:  # CSV
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="inventario_{timezone.now().strftime("%Y%m%d")}.csv"'
            df.to_csv(response, index=False, encoding='utf-8-sig')
        
        return response
    
    @extend_schema(tags=['Export'])
    @action(detail=False, methods=['get'])
    def movements(self, request):
        """Exportar movimientos de inventario a CSV o Excel"""
        format_type = request.query_params.get('format', 'csv')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        movement_type = request.query_params.get('movement_type')
        
        # Construir queryset
        queryset = MovementInventory.objects.select_related(
            'variant__product', 'supplier'
        ).all()
        
        # Aplicar filtros
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=end_date)
            except ValueError:
                pass
        
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)
        
        # Preparar datos
        data = []
        for movement in queryset:
            data.append({
                'ID Movimiento': movement.id,
                'Tipo': movement.get_movement_type_display(),
                'Producto': movement.variant.product.name,
                'Marca': movement.variant.product.brand,
                'Variante': f"{movement.variant.get_gender_display()} - {movement.variant.color} - {movement.variant.size}",
                'Cantidad': movement.quantity,
                'Proveedor': movement.supplier.name if movement.supplier else 'N/A',
                'Observación': movement.observation or '',
                'Fecha': movement.created_at.strftime('%Y-%m-%d %H:%M'),
                'Creado por': movement.created_by
            })
        
        # Crear DataFrame
        df = pd.DataFrame(data)
        
        if format_type.lower() == 'excel':
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="movimientos_{timezone.now().strftime("%Y%m%d")}.xlsx"'
            df.to_excel(response, index=False, engine='openpyxl')
        else:  # CSV
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="movimientos_{timezone.now().strftime("%Y%m%d")}.csv"'
            df.to_csv(response, index=False, encoding='utf-8-sig')
        
        return response
    
    @extend_schema(tags=['Export'])
    @action(detail=False, methods=['get'])
    def suppliers_report(self, request):
        """Exportar reporte de proveedores a CSV o Excel"""
        format_type = request.query_params.get('format', 'csv')
        days = request.query_params.get('days', 90)
        
        try:
            days = int(days)
        except ValueError:
            days = 90
        
        start_date = timezone.now().date() - timedelta(days=days)
        
        # Datos de proveedores con sus compras
        suppliers_data = Supplier.objects.filter(
            movements__movement_type=MovementInventory.MovementType.PURCHASE,
            movements__created_at__date__gte=start_date
        ).annotate(
            total_compras=Count('movements'),
            total_cantidad=Sum('movements__quantity'),
            total_productos=Count('movements__variant', distinct=True),
            ultima_compra=Max('movements__created_at')
        ).order_by('-total_cantidad')
        
        # Preparar datos
        data = []
        for supplier in suppliers_data:
            data.append({
                'ID Proveedor': supplier.id,
                'Nombre': supplier.name,
                'NIT': supplier.nit or 'N/A',
                'Teléfono': supplier.phone or 'N/A',
                'Dirección': supplier.address or 'N/A',
                'Total Compras': supplier.total_compras,
                'Total Cantidad': supplier.total_cantidad or 0,
                'Productos Diferentes': supplier.total_productos,
                'Última Compra': supplier.ultima_compra.strftime('%Y-%m-%d') if supplier.ultima_compra else 'N/A',
                'Estado': 'Activo' if supplier.is_active else 'Inactivo',
                'Fecha Creación': supplier.created_at.strftime('%Y-%m-%d')
            })
        
        # Crear DataFrame
        df = pd.DataFrame(data)
        
        if format_type.lower() == 'excel':
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="proveedores_{timezone.now().strftime("%Y%m%d")}.xlsx"'
            df.to_excel(response, index=False, engine='openpyxl')
        else:  # CSV
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="proveedores_{timezone.now().strftime("%Y%m%d")}.csv"'
            df.to_csv(response, index=False, encoding='utf-8-sig')
        
        return response
