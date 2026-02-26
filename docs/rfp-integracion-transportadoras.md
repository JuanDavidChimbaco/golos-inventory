# RFP Express: Integración de Transportadoras (48h)

Fecha: 2026-02-26  
Solicitante: Golos Store (ecommerce + backend Django)

## 1) Objetivo
Seleccionar proveedor de logística para:
- Cotización automática por pedido.
- Creación automática de guías al confirmar pago.
- Tracking y webhooks para actualizar estados (`shipped`, `delivered`) sin intervención manual.

## 2) Contexto técnico actual
- Backend: Django + DRF.
- Flujo actual: checkout -> pago Wompi -> actualización de orden.
- Ya existe endpoint webhook de shipping e idempotencia por evento.
- Buscamos integración por API REST (JSON) y webhook firmado (HMAC/JWT).

## 3) Alcance requerido (MVP)
- `Quote`: cotizar envío por destino/peso/volumen.
- `Create shipment`: generar guía y número de tracking.
- `Label`: URL o binario de etiqueta.
- `Tracking`: consulta por tracking.
- `Webhook`: eventos de tránsito y entrega.
- `Cancel shipment` (deseable en MVP, obligatorio en fase 2).

## 4) Requisitos técnicos obligatorios
- API documentada (OpenAPI/Swagger o equivalente).
- Sandbox/UAT funcional.
- Autenticación API (API key/OAuth/JWT).
- Webhooks con firma verificable.
- Reintentos y política de duplicados (event id único).
- SLA API y límites de rate.
- Soporte técnico con tiempos de respuesta definidos.

## 5) Requisitos comerciales
- Estructura de tarifas por guía.
- Costos adicionales (recaudos, sobrepeso, devoluciones, reintentos).
- Cobertura nacional y tiempos estimados por ciudad.
- ANS de cumplimiento y penalizaciones por incumplimiento.
- Facturación y condiciones de pago.
- Sin volumen mínimo mensual obligatorio (requisito excluyente).

## 6) Respuesta solicitada al proveedor
Enviar en una sola respuesta:
1. Documentación API + credenciales sandbox.  
2. Tarifario base + recargos y condiciones.  
3. Cobertura y SLA por región.  
4. Seguridad de webhooks (firma/cifrado).  
5. Contacto técnico/comercial y horario de soporte.  
6. Tiempo estimado de go-live.

## 7) Matriz de evaluación (100 puntos)
- Costo total por envío (30)
- Cobertura + SLA real (25)
- Calidad API + webhooks + seguridad (25)
- Tiempo de implementación (10)
- Soporte operativo/comercial (10)

Regla de descarte:
- Se descarta automáticamente cualquier proveedor que exija mínimo mensual obligatorio de envíos.

## 8) Cronograma de decisión
- Día 0: envío de RFP.
- Día 1: recepción de documentación y credenciales.
- Día 2: prueba técnica + scoring.
- Día 3: selección de proveedor y arranque de integración productiva.

## 9) Correo sugerido (plantilla)
Asunto: Solicitud RFP Express integración API logística – Golos Store

Hola equipo [Proveedor],

Estamos evaluando proveedor logístico para integración API en ecommerce (Django).  
Necesitamos cotización, creación de guía, tracking y webhooks seguros.  
Adjuntamos RFP express (alcance MVP + criterios).  
¿Nos pueden compartir en 24 horas documentación API, credenciales sandbox, tarifas y cobertura?

Gracias,  
[Nombre / Cargo]  
Golos Store
