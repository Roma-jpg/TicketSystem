# apps/notifications/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return
        self.group_name = f"notifications_user_{self.user.pk}"
        if self.channel_layer is not None:
            await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.channel_layer is not None:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notification_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "notification_update",
            "unread_count": event.get("unread_count", 0),
            "new_notification": event.get("new_notification"),
        }))