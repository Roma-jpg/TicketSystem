import json
from channels.generic.websocket import AsyncWebsocketConsumer


class TicketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "tickets"
        if self.channel_layer is not None:
            await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.channel_layer is not None:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def ticket_update(self, event):
        await self.send(text_data=json.dumps({
            "event": event.get("event"),
            "ticket": event.get("ticket"),
            "message": event.get("message"),
        }, default=str))