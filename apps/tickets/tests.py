from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User


class TicketTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="teacher",
            password="password123",
        )

    def test_create_ticket(self):

        self.client.login(
            username="teacher",
            password="password123",
        )

        response = self.client.post(
            reverse(
                "tickets:ticket_create"
            ),
            {
                "room_number": "101",
                "device_type": "desktop",
                "category": "hardware",
                "urgency": "high",
                "description": "Broken PC",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )
