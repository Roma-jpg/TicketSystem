# apps/tickets/consumers.py
import json
import redis
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

redis_client = redis.Redis.from_url(settings.REDIS_URL)


class TicketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.ticket_id = self.scope["url_route"]["kwargs"]["ticket_id"]
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = f"ticket_{self.ticket_id}"
        if self.channel_layer is not None:
            await self.channel_layer.group_add(self.group_name, self.channel_name)

        # Mark user as viewing this ticket
        redis_client.sadd(f"viewing_ticket:{self.ticket_id}", self.user.pk)

        await self.accept()

    async def disconnect(self, close_code):
        if self.channel_layer is not None:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        redis_client.srem(f"viewing_ticket:{self.ticket_id}", self.user.pk)

    async def ticket_update(self, event):
        """Forward any ticket_update event (status change, comment, etc.) to the browser."""
        await self.send(text_data=json.dumps(event, default=str))