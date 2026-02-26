# Procedimiento Operativo: Pedidos de Tienda Online

Fecha: 2026-02-26  
Aplica para: personal operativo de tienda (panel `Store Ops`)

## 1) Objetivo
Estandarizar qué hacer cuando entra un pedido online para evitar errores y asegurar trazabilidad.

## 2) Estados del pedido (referencia rápida)
- `pending`: pedido creado, pendiente de pago.
- `paid`: pago confirmado.
- `processing`: pedido en preparación.
- `shipped`: pedido enviado (con guía).
- `delivered`: pedido entregado.
- `completed`: pedido cerrado.
- `canceled`: pedido cancelado.

## 3) Flujo operativo diario (paso a paso)

### Paso 1: Revisar panel
1. Entrar a `Store Ops`.
2. Filtrar por `pending`, `paid`, `processing`.
3. Priorizar pedidos más antiguos primero.

### Paso 2: Validar pago
1. Si el pedido está en `paid`, continuar a preparación.
2. Si el pedido sigue en `pending` pero ya se confirmó pago por otro canal:
   - usar botón `Marcar pago manual`.
   - dejar nota operativa si aplica.

### Paso 3: Preparar pedido
1. Verificar referencias, talla/color y cantidad.
2. Empacar.
3. Dejar pedido listo para despacho.
4. Si aplica, pasar estado a `processing`.

### Paso 4: Registrar guía de envío
1. Llevar paquete a transportadora (Servientrega, Interrapidísimo, etc.) o generar guía por portal.
2. En el panel, abrir `Registrar guía manual` en la orden.
3. Completar mínimo:
   - `carrier` (transportadora)
   - `tracking_number` (número de guía)
   - `shipping_cost` (valor pagado)
4. Guardar.
5. Confirmar que la orden quede en `shipped` (si estaba `paid/processing`).

### Paso 5: Seguimiento y entrega
1. Revisar envíos `shipped` diariamente.
2. Cuando la transportadora confirme entrega:
   - actualizar a `delivered` (manual u webhook automático).
3. Verificar que la fecha de entrega quede registrada.

### Paso 6: Cierre
1. Pasar pedidos `delivered` a `completed` (manual o por automatización configurada).
2. Archivar incidencias del día.

## 4) Checklist por pedido
- [ ] Pago confirmado
- [ ] Producto correcto y completo
- [ ] Empaque realizado
- [ ] Guía registrada (carrier + tracking + costo)
- [ ] Estado en `shipped`
- [ ] Entrega confirmada (`delivered`)
- [ ] Cierre (`completed`)

## 5) Manejo de excepciones

### Pedido sin stock al preparar
1. No despachar.
2. Notificar responsable.
3. Definir reemplazo o cancelación.
4. Si se cancela, estado `canceled` con nota.

### Error de guía (tracking mal digitado)
1. Editar/re-registrar guía correcta en la orden.
2. Verificar que no se duplique tracking en otra orden.

### Cliente solicita cancelación
1. Si no fue despachado: cancelar (`canceled`) y registrar nota.
2. Si ya fue despachado: gestionar retorno según política.

## 6) Reglas de calidad operativa
- No despachar sin guía registrada.
- No cerrar (`completed`) sin confirmación de entrega.
- Toda acción manual debe quedar registrada en sistema.
- Mantener tiempos internos sugeridos:
  - `paid` -> `processing`: <= 30 min
  - `processing` -> `shipped`: mismo día hábil

## 7) Campos mínimos para guía manual
- Transportadora (`carrier`)
- Número de guía (`tracking_number`)
- Costo (`shipping_cost`)

Opcionales recomendados:
- Servicio (`service`)
- Referencia proveedor (`provider_reference`)
- URL de etiqueta/comprobante (`label_url`)

## 8) Control de margen online (anti perdida)
- El checkout ahora calcula rentabilidad estimada con:
  - costo producto
  - comisión Wompi
  - envío estimado (zona/peso)
  - empaque y riesgo
- Si `STORE_MARGIN_GUARD_ENABLED=True`, el sistema bloquea pedidos con margen por debajo de `STORE_MARGIN_MIN_PERCENT`.
- Configuración por entorno (`.env`):
  - `STORE_MARGIN_GUARD_ENABLED`
  - `STORE_MARGIN_MIN_PERCENT`
  - `STORE_MARGIN_WOMPI_PERCENT`
  - `STORE_MARGIN_WOMPI_FIXED_FEE`
  - `STORE_MARGIN_WOMPI_VAT_PERCENT`
  - `STORE_MARGIN_PACKAGING_COST`
  - `STORE_MARGIN_RISK_PERCENT`
  - `STORE_MARGIN_DEFAULT_WEIGHT_PER_ITEM_GRAMS`
  - `STORE_MARGIN_DEFAULT_SHIPPING_COST`
  - `STORE_MARGIN_SHIPPING_COST_MATRIX`
