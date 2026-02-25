"""
Views para operaciones batch (masivas)
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from drf_spectacular.utils import extend_schema
from ..models import ProductVariant, Product, Supplier
from ..core.services import create_purchase, create_adjustment
from ..core.api_responses import error_response, success_response

@extend_schema(tags=['Batch'])
class BatchOperationsViewSet(viewsets.GenericViewSet):
    """
    ViewSet para operaciones batch (masivas)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def update_prices(self, request):
        """Actualizar precios masivamente"""
        updates = request.data.get('updates', [])
        
        if not updates:
            return error_response(
                detail='Se requieren actualizaciones',
                code='MISSING_UPDATES',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            with transaction.atomic():
                updated_count = 0
                errors = []
                
                for update in updates:
                    variant_id = update.get('variant_id')
                    new_price = update.get('price')
                    new_cost = update.get('cost')
                    
                    if not variant_id:
                        errors.append({'error': 'variant_id requerido', 'update': update})
                        continue
                    
                    try:
                        variant = ProductVariant.objects.get(id=variant_id)
                        
                        if new_price is not None and new_price > 0:
                            variant.price = new_price
                        
                        if new_cost is not None and new_cost > 0:
                            variant.cost = new_cost
                        
                        variant.updated_by = request.user.username
                        variant.save()
                        updated_count += 1
                        
                    except ProductVariant.DoesNotExist:
                        errors.append({'error': f'Variante {variant_id} no encontrada', 'update': update})
                    except Exception as e:
                        errors.append({'error': str(e), 'update': update})
                
                return success_response(
                    detail=f'Se actualizaron {updated_count} variantes',
                    code='BATCH_PRICES_UPDATED',
                    updated_count=updated_count,
                    errors_count=len(errors),
                    errors=errors,
                )
                
        except Exception as e:
            return error_response(
                detail=f'Error en actualización masiva: {str(e)}',
                code='BATCH_PRICES_UPDATE_FAILED',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
    
    @action(detail=False, methods=['post'])
    def update_stock_minimum(self, request):
        """Actualizar stock mínimo masivamente"""
        updates = request.data.get('updates', [])
        
        if not updates:
            return error_response(
                detail='Se requieren actualizaciones',
                code='MISSING_UPDATES',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            with transaction.atomic():
                updated_count = 0
                errors = []
                
                for update in updates:
                    variant_id = update.get('variant_id')
                    new_minimum = update.get('stock_minimum')
                    
                    if not variant_id or new_minimum is None:
                        errors.append({'error': 'variant_id y stock_minimum requeridos', 'update': update})
                        continue
                    
                    try:
                        variant = ProductVariant.objects.get(id=variant_id)
                        variant.stock_minimum = max(0, int(new_minimum))
                        variant.updated_by = request.user.username
                        variant.save()
                        updated_count += 1
                        
                    except ProductVariant.DoesNotExist:
                        errors.append({'error': f'Variante {variant_id} no encontrada', 'update': update})
                    except Exception as e:
                        errors.append({'error': str(e), 'update': update})
                
                return success_response(
                    detail=f'Se actualizaron {updated_count} variantes',
                    code='BATCH_STOCK_MINIMUM_UPDATED',
                    updated_count=updated_count,
                    errors_count=len(errors),
                    errors=errors,
                )
                
        except Exception as e:
            return error_response(
                detail=f'Error en actualización masiva: {str(e)}',
                code='BATCH_STOCK_MINIMUM_UPDATE_FAILED',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
    
    @action(detail=False, methods=['post'])
    def create_products_batch(self, request):
        """Crear múltiples productos masivamente"""
        products_data = request.data.get('products', [])
        
        if not products_data:
            return error_response(
                detail='Se requieren productos',
                code='MISSING_PRODUCTS',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            with transaction.atomic():
                created_count = 0
                errors = []
                
                for product_data in products_data:
                    try:
                        # Crear producto
                        product = Product.objects.create(
                            name=product_data['name'],
                            brand=product_data.get('brand', ''),
                            description=product_data.get('description', ''),
                            created_by=request.user.username,
                            updated_by=request.user.username
                        )
                        
                        # Crear variantes si se proporcionan
                        variants = product_data.get('variants', [])
                        for variant_data in variants:
                            ProductVariant.objects.create(
                                product=product,
                                gender=variant_data.get('gender', 'unisex'),
                                color=variant_data.get('color', ''),
                                size=variant_data.get('size', ''),
                                price=variant_data.get('price', 0),
                                cost=variant_data.get('cost', 0),
                                stock_minimum=variant_data.get('stock_minimum', 1),
                                created_by=request.user.username,
                                updated_by=request.user.username
                            )
                        
                        created_count += 1
                        
                    except Exception as e:
                        errors.append({'error': str(e), 'product': product_data})
                
                return success_response(
                    detail=f'Se crearon {created_count} productos',
                    code='BATCH_PRODUCTS_CREATED',
                    created_count=created_count,
                    errors_count=len(errors),
                    errors=errors,
                )
                
        except Exception as e:
            return error_response(
                detail=f'Error en creación masiva: {str(e)}',
                code='BATCH_PRODUCTS_CREATE_FAILED',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
    
    @action(detail=False, methods=['post'])
    def bulk_purchase(self, request):
        """Crear compras masivas desde múltiples proveedores"""
        purchases = request.data.get('purchases', [])
        
        if not purchases:
            return error_response(
                detail='Se requieren compras',
                code='MISSING_PURCHASES',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            with transaction.atomic():
                created_count = 0
                errors = []
                total_movements = []
                
                for purchase_data in purchases:
                    try:
                        supplier_id = purchase_data.get('supplier_id')
                        items = purchase_data.get('items', [])
                        observation = purchase_data.get('observation', 'Compra masiva')
                        
                        if not supplier_id or not items:
                            errors.append({'error': 'supplier_id e items requeridos', 'purchase': purchase_data})
                            continue
                        
                        supplier = Supplier.objects.get(id=supplier_id)
                        
                        for item in items:
                            movement = create_purchase(
                                variant_id=item['variant_id'],
                                quantity=item['quantity'],
                                unit_cost=item.get('unit_cost', 0),
                                supplier_id=supplier.id,
                                supplier_name=supplier.name,
                                user=request.user
                            )
                            
                            if observation:
                                movement.observation = observation
                                movement.save()
                            
                            total_movements.append(movement)
                        
                        created_count += 1
                        
                    except Supplier.DoesNotExist:
                        errors.append({'error': f'Proveedor {supplier_id} no encontrado', 'purchase': purchase_data})
                    except Exception as e:
                        errors.append({'error': str(e), 'purchase': purchase_data})
                
                return success_response(
                    detail=f'Se procesaron {created_count} compras con {len(total_movements)} movimientos',
                    code='BATCH_PURCHASES_CREATED',
                    created_count=created_count,
                    total_movements=len(total_movements),
                    errors_count=len(errors),
                    errors=errors,
                )
                
        except Exception as e:
            return error_response(
                detail=f'Error en compra masiva: {str(e)}',
                code='BATCH_PURCHASES_CREATE_FAILED',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
    
    @action(detail=False, methods=['post'])
    def bulk_adjustments(self, request):
        """Crear ajustes masivos de inventario"""
        adjustments = request.data.get('adjustments', [])
        
        if not adjustments:
            return error_response(
                detail='Se requieren ajustes',
                code='MISSING_ADJUSTMENTS',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            with transaction.atomic():
                created_count = 0
                errors = []
                total_movements = []
                
                for adjustment_data in adjustments:
                    try:
                        variant_id = adjustment_data.get('variant_id')
                        quantity = adjustment_data.get('quantity')
                        reason = adjustment_data.get('reason', 'Ajuste masivo')
                        
                        if variant_id is None or quantity is None:
                            errors.append({'error': 'variant_id y quantity requeridos', 'adjustment': adjustment_data})
                            continue
                        
                        movement = create_adjustment(
                            variant_id=variant_id,
                            quantity=quantity,
                            reason=reason,
                            user=request.user
                        )
                        
                        total_movements.append(movement)
                        created_count += 1
                        
                    except Exception as e:
                        errors.append({'error': str(e), 'adjustment': adjustment_data})
                
                return success_response(
                    detail=f'Se crearon {created_count} ajustes',
                    code='BATCH_ADJUSTMENTS_CREATED',
                    created_count=created_count,
                    total_movements=len(total_movements),
                    errors_count=len(errors),
                    errors=errors,
                )
                
        except Exception as e:
            return error_response(
                detail=f'Error en ajuste masivo: {str(e)}',
                code='BATCH_ADJUSTMENTS_CREATE_FAILED',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
    
    @action(detail=False, methods=['post'])
    def toggle_products_status(self, request):
        """Activar/desactivar productos masivamente"""
        product_ids = request.data.get('product_ids', [])
        action_type = request.data.get('action', 'toggle')  # 'activate', 'deactivate', 'toggle'
        
        if not product_ids:
            return error_response(
                detail='Se requieren product_ids',
                code='MISSING_PRODUCT_IDS',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            with transaction.atomic():
                updated_count = 0
                errors = []
                
                for product_id in product_ids:
                    try:
                        product = Product.objects.get(id=product_id)
                        
                        if action_type == 'activate':
                            product.active = True
                        elif action_type == 'deactivate':
                            product.active = False
                        else:  # toggle
                            product.active = not product.active
                        
                        product.updated_by = request.user.username
                        product.save()
                        updated_count += 1
                        
                    except Product.DoesNotExist:
                        errors.append({'error': f'Producto {product_id} no encontrado'})
                    except Exception as e:
                        errors.append({'error': str(e), 'product_id': product_id})
                
                return success_response(
                    detail=f'Se actualizaron {updated_count} productos',
                    code='BATCH_PRODUCTS_STATUS_UPDATED',
                    updated_count=updated_count,
                    errors_count=len(errors),
                    errors=errors,
                )
                
        except Exception as e:
            return error_response(
                detail=f'Error en actualización masiva: {str(e)}',
                code='BATCH_PRODUCTS_STATUS_UPDATE_FAILED',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
    
    @action(detail=False, methods=['post'])
    def toggle_variants_status(self, request):
        """Activar/desactivar variantes masivamente"""
        variant_ids = request.data.get('variant_ids', [])
        action_type = request.data.get('action', 'toggle')  # 'activate', 'deactivate', 'toggle'
        
        if not variant_ids:
            return error_response(
                detail='Se requieren variant_ids',
                code='MISSING_VARIANT_IDS',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            with transaction.atomic():
                updated_count = 0
                errors = []
                
                for variant_id in variant_ids:
                    try:
                        variant = ProductVariant.objects.get(id=variant_id)
                        
                        if action_type == 'activate':
                            variant.active = True
                        elif action_type == 'deactivate':
                            variant.active = False
                        else:  # toggle
                            variant.active = not variant.active
                        
                        variant.updated_by = request.user.username
                        variant.save()
                        updated_count += 1
                        
                    except ProductVariant.DoesNotExist:
                        errors.append({'error': f'Variante {variant_id} no encontrada'})
                    except Exception as e:
                        errors.append({'error': str(e), 'variant_id': variant_id})
                
                return success_response(
                    detail=f'Se actualizaron {updated_count} variantes',
                    code='BATCH_VARIANTS_STATUS_UPDATED',
                    updated_count=updated_count,
                    errors_count=len(errors),
                    errors=errors,
                )
                
        except Exception as e:
            return error_response(
                detail=f'Error en actualización masiva: {str(e)}',
                code='BATCH_VARIANTS_STATUS_UPDATE_FAILED',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
