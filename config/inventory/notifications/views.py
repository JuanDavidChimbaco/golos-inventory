"""
Views para sistema de notificaciones
"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from ..models import (
    ProductVariant, MovementInventory, Product, Supplier
)
from ..core.services import low_stock_variants
from ..core.api_responses import success_response


class NotificationViewSet(viewsets.GenericViewSet):
    """
    ViewSet para sistema de notificaciones
    """
    permission_classes = [permissions.IsAuthenticated]
    
    # Tags para documentación Swagger
    tags = ['Notifications']
    
    @extend_schema(tags=['Notifications'])
    @action(detail=False, methods=['get'])
    def low_stock_alerts(self, request):
        """Alertas de stock bajo"""
        threshold = request.query_params.get('threshold', None)
        
        low_stock = low_stock_variants()
        
        if threshold:
            try:
                threshold = int(threshold)
                low_stock = low_stock.annotate(
                    stock=Sum('movements__quantity')
                ).filter(stock__lte=threshold)
            except ValueError:
                pass
        
        # Categorizar por nivel de urgencia
        critical = []  # 0 unidades
        warning = []   # Por debajo del mínimo
        info = []      # Cerca del mínimo (80% del stock mínimo)
        
        for variant in low_stock:
            current_stock = variant.stock
            
            if current_stock <= 0:
                critical.append({
                    'id': variant.id,
                    'product_name': variant.product.name,
                    'variant_info': f"{variant.get_gender_display()} - {variant.color} - {variant.size}",
                    'current_stock': current_stock,
                    'stock_minimum': variant.stock_minimum,
                    'deficit': -current_stock,
                    'urgency': 'critical',
                    'message': 'SIN STOCK - Requiere reposición inmediata'
                })
            elif current_stock < variant.stock_minimum:
                warning.append({
                    'id': variant.id,
                    'product_name': variant.product.name,
                    'variant_info': f"{variant.get_gender_display()} - {variant.color} - {variant.size}",
                    'current_stock': current_stock,
                    'stock_minimum': variant.stock_minimum,
                    'deficit': variant.stock_minimum - current_stock,
                    'urgency': 'warning',
                    'message': f'Stock bajo - Faltan {variant.stock_minimum - current_stock} unidades'
                })
            elif current_stock <= (variant.stock_minimum * 0.8):
                info.append({
                    'id': variant.id,
                    'product_name': variant.product.name,
                    'variant_info': f"{variant.get_gender_display()} - {variant.color} - {variant.size}",
                    'current_stock': current_stock,
                    'stock_minimum': variant.stock_minimum,
                    'deficit': 0,
                    'urgency': 'info',
                    'message': 'Stock cercano al mínimo - Considerar reposición'
                })
        
        return success_response(
            detail='Alertas de stock bajo obtenidas correctamente',
            code='NOTIFICATIONS_LOW_STOCK_ALERTS_OK',
            total_alerts=len(critical) + len(warning) + len(info),
            critical=critical,
            warning=warning,
            info=info,
            summary={
                'critical_count': len(critical),
                'warning_count': len(warning),
                'info_count': len(info)
            },
        )
    
    @extend_schema(tags=['Notifications'])
    @action(detail=False, methods=['get'])
    def daily_summary(self, request):
        """Resumen diario de actividades"""
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # Ventas de hoy
        today_sales = MovementInventory.objects.filter(
            movement_type=MovementInventory.MovementType.SALE_OUT,
            created_at__date=today
        ).count()
        
        # Compras de hoy
        today_purchases = MovementInventory.objects.filter(
            movement_type=MovementInventory.MovementType.PURCHASE,
            created_at__date=today
        ).count()
        
        # Productos nuevos hoy
        today_products = Product.objects.filter(
            created_at__date=today
        ).count()
        
        # Ajustes hoy
        today_adjustments = MovementInventory.objects.filter(
            movement_type=MovementInventory.MovementType.ADJUSTMENT,
            created_at__date=today
        ).count()
        
        # Comparación con ayer
        yesterday_sales = MovementInventory.objects.filter(
            movement_type=MovementInventory.MovementType.SALE_OUT,
            created_at__date=yesterday
        ).count()
        
        sales_change = ((today_sales - yesterday_sales) / yesterday_sales * 100) if yesterday_sales > 0 else 0
        
        return success_response(
            detail='Resumen diario obtenido correctamente',
            code='NOTIFICATIONS_DAILY_SUMMARY_OK',
            date=today.strftime('%Y-%m-%d'),
            activities={
                'sales': {
                    'today': today_sales,
                    'yesterday': yesterday_sales,
                    'change_percent': round(sales_change, 2)
                },
                'purchases': today_purchases,
                'new_products': today_products,
                'adjustments': today_adjustments
            },
            alerts_count=low_stock_variants().count(),
        )
    
    @extend_schema(tags=['Notifications'])
    @action(detail=False, methods=['get'])
    def supplier_recommendations(self, request):
        """Recomendaciones de proveedores basadas en stock bajo"""
        low_stock = low_stock_variants()
        
        # Agrupar por proveedores preferidos (relación real: Supplier.preferred_products)
        supplier_recommendations = {}
        
        for variant in low_stock:
            product = variant.product

            suppliers = Supplier.objects.filter(
                preferred_products=product,
                is_active=True,
            ).distinct()

            for supplier in suppliers:
                supplier_name = supplier.name
                if supplier_name not in supplier_recommendations:
                    supplier_recommendations[supplier_name] = {
                        'supplier_name': supplier_name,
                        'supplier_id': supplier.id,
                        'products_needed': [],
                        'total_variants': 0
                    }

                supplier_recommendations[supplier_name]['products_needed'].append({
                    'product_name': product.name,
                    'variant_info': f"{variant.get_gender_display()} - {variant.color} - {variant.size}",
                    'current_stock': variant.stock,
                    'stock_minimum': variant.stock_minimum,
                    'recommended_quantity': max(0, variant.stock_minimum - variant.stock)
                })
                supplier_recommendations[supplier_name]['total_variants'] += 1
        
        # Ordenar por cantidad de variantes necesitadas
        recommendations = sorted(
            supplier_recommendations.values(),
            key=lambda x: x['total_variants'],
            reverse=True
        )
        
        return success_response(
            detail='Recomendaciones de proveedores obtenidas correctamente',
            code='NOTIFICATIONS_SUPPLIER_RECOMMENDATIONS_OK',
            recommendations=recommendations[:10],  # Top 10
            total_suppliers=len(recommendations),
            total_variants_needed=len(low_stock),
        )
    
    @extend_schema(tags=['Notifications'])
    @action(detail=False, methods=['get'])
    def movement_anomalies(self, request):
        """Detectar anomalías en movimientos de inventario"""
        days = request.query_params.get('days', 7)
        
        try:
            days = int(days)
        except ValueError:
            days = 7
        
        start_date = timezone.now().date() - timedelta(days=days)
        
        # Movimientos con cantidades inusualmente altas
        high_quantity_movements = MovementInventory.objects.filter(
            created_at__date__gte=start_date
        ).filter(
            quantity__gt=100  # Más de 100 unidades
        ).select_related('variant__product', 'supplier').order_by('-quantity')[:10]
        
        # Ajustes frecuentes (posibles problemas de control)
        frequent_adjustments = MovementInventory.objects.filter(
            movement_type=MovementInventory.MovementType.ADJUSTMENT,
            created_at__date__gte=start_date
        ).values('variant__product__name').annotate(
            adjustment_count=Count('id')
        ).filter(adjustment_count__gt=3).order_by('-adjustment_count')[:10]
        
        # Devoluciones inusualmente altas
        high_returns = MovementInventory.objects.filter(
            movement_type__in=[
                MovementInventory.MovementType.RETURN,
                MovementInventory.MovementType.SALE_RETURN
            ],
            created_at__date__gte=start_date,
            quantity__lt=-50  # Devolución de más de 50 unidades
        ).select_related('variant__product', 'supplier').order_by('quantity')[:10]
        
        anomalies = []
        
        # Procesar movimientos de alta cantidad
        for movement in high_quantity_movements:
            anomalies.append({
                'type': 'high_quantity',
                'severity': 'warning',
                'message': f'Movimiento inusualmente alto: {abs(movement.quantity)} unidades',
                'details': {
                    'product': movement.variant.product.name,
                    'quantity': movement.quantity,
                    'date': movement.created_at.strftime('%Y-%m-%d %H:%M'),
                    'user': movement.created_by
                }
            })
        
        # Procesar ajustes frecuentes
        for adjustment in frequent_adjustments:
            anomalies.append({
                'type': 'frequent_adjustments',
                'severity': 'info',
                'message': f'Ajustes frecuentes: {adjustment["adjustment_count"]} en {days} días',
                'details': {
                    'product': adjustment['variant__product__name'],
                    'adjustment_count': adjustment['adjustment_count']
                }
            })
        
        # Procesar devoluciones altas
        for movement in high_returns:
            anomalies.append({
                'type': 'high_return',
                'severity': 'warning',
                'message': f'Devolución inusualmente alta: {abs(movement.quantity)} unidades',
                'details': {
                    'product': movement.variant.product.name,
                    'quantity': movement.quantity,
                    'date': movement.created_at.strftime('%Y-%m-%d %H:%M'),
                    'user': movement.created_by
                }
            })
        
        return success_response(
            detail='Anomalias de movimientos obtenidas correctamente',
            code='NOTIFICATIONS_MOVEMENT_ANOMALIES_OK',
            total_anomalies=len(anomalies),
            period_days=days,
            anomalies=anomalies,
            summary={
                'high_quantity': len([a for a in anomalies if a['type'] == 'high_quantity']),
                'frequent_adjustments': len([a for a in anomalies if a['type'] == 'frequent_adjustments']),
                'high_returns': len([a for a in anomalies if a['type'] == 'high_return'])
            },
        )
    
    @extend_schema(tags=['Notifications'])
    @action(detail=False, methods=['get'])
    def performance_metrics(self, request):
        """Métricas de rendimiento del inventario"""
        last_month = timezone.now().date() - timedelta(days=30)
        
        # Rotación de inventario (productos vendidos vs productos totales)
        total_products = ProductVariant.objects.filter(active=True).count()
        sold_products = MovementInventory.objects.filter(
            movement_type=MovementInventory.MovementType.SALE_OUT,
            created_at__date__gte=last_month
        ).values('variant').distinct().count()
        
        rotation_rate = (sold_products / total_products * 100) if total_products > 0 else 0
        
        # Precisión de inventario (ajustes vs movimientos totales)
        total_movements = MovementInventory.objects.filter(
            created_at__date__gte=last_month
        ).count()
        adjustments = MovementInventory.objects.filter(
            movement_type=MovementInventory.MovementType.ADJUSTMENT,
            created_at__date__gte=last_month
        ).count()
        
        accuracy_rate = ((total_movements - adjustments) / total_movements * 100) if total_movements > 0 else 100
        
        # Tasa de devoluciones
        sales_out = MovementInventory.objects.filter(
            movement_type=MovementInventory.MovementType.SALE_OUT,
            created_at__date__gte=last_month
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        returns = MovementInventory.objects.filter(
            movement_type=MovementInventory.MovementType.SALE_RETURN,
            created_at__date__gte=last_month
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        return_rate = (abs(returns) / sales_out * 100) if sales_out > 0 else 0
        
        return success_response(
            detail='Metricas de rendimiento obtenidas correctamente',
            code='NOTIFICATIONS_PERFORMANCE_METRICS_OK',
            period='Últimos 30 días',
            metrics={
                'inventory_rotation': {
                    'value': round(rotation_rate, 2),
                    'description': 'Porcentaje de productos con movimiento',
                    'status': 'good' if rotation_rate > 70 else 'warning' if rotation_rate > 40 else 'critical'
                },
                'inventory_accuracy': {
                    'value': round(accuracy_rate, 2),
                    'description': 'Precisión del control de inventario',
                    'status': 'good' if accuracy_rate > 95 else 'warning' if accuracy_rate > 85 else 'critical'
                },
                'return_rate': {
                    'value': round(return_rate, 2),
                    'description': 'Tasa de devoluciones',
                    'status': 'good' if return_rate < 5 else 'warning' if return_rate < 15 else 'critical'
                }
            },
            summary={
                'total_products': total_products,
                'sold_products': sold_products,
                'total_movements': total_movements,
                'adjustments': adjustments,
                'sales_quantity': sales_out,
                'returns_quantity': abs(returns)
            },
        )
