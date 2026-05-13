# apps/tickets/realtime.py
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def serialize_ticket(ticket):
    return {
        "id": str(ticket.pk),
        "ticket_number": ticket.ticket_number,
        "status": ticket.status,
        "urgency": ticket.urgency,
        "room_number": ticket.room_number,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
    }


def broadcast_ticket_event(ticket, event_name, message="", data=None):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    payload = {
        "type": "ticket_update",
        "event": event_name,
        "ticket": serialize_ticket(ticket),
        "message": message,
    }
    if data:
        payload.update(data)
    try:
        async_to_sync(channel_layer.group_send)(f"ticket_{ticket.pk}", payload)
    except Exception:
        pass