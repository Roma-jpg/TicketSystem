from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Ticket, TicketHistory


@receiver(post_save, sender=Ticket)
def create_history(sender, instance, created, **kwargs):

	if created:
		TicketHistory.objects.create(
			ticket=instance,
			new_status=instance.status,
			changed_by=instance.created_by,
		)