import json
from channels.generic.websocket import AsyncWebsocketConsumer

class StockConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Unimos a los clientes al grupo general de stock
        self.group_name = "stock_updates"
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        # Salir del grupo
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Recibir mensaje desde el grupo (enviado por las signals de Django)
    async def stock_update(self, event):
        # event es un diccionario con la informacion del stock
        await self.send(text_data=json.dumps({
            "type": "stock_update",
            "variant_id": event["variant_id"],
            "new_stock": event["new_stock"]
        }))

    async def system_alert(self, event):
        # Evento genérico para notificaciones del sistema
        await self.send(text_data=json.dumps({
            "type": "system_alert",
            "message": event.get("message", "Nueva alerta")
        }))
