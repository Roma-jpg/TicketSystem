from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    class Roles(models.TextChoices):
        STUDENT = "student", "Студент"
        TEACHER = "teacher", "Преподаватель"
        IT_STAFF = "it_staff", "ИТ-сотрудник"
        IT_ADMIN = "it_admin", "ИТ-администратор"
        PRINCIPAL = "principal", "Директор"

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.TEACHER,
        db_index=True,
    )

    room = models.CharField(
        max_length=32,
        blank=True,
    )

    def is_it(self):
        return self.role in [
            self.Roles.IT_STAFF,
            self.Roles.IT_ADMIN
        ]

    def is_principal(self):
        return self.role == self.Roles.PRINCIPAL

    def __str__(self):
        return self.username
