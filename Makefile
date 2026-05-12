.PHONY: help run migrate makemigrations shell test collectstatic

help:
	@echo "Available commands: run, migrate, makemigrations, shell, test, collectstatic"

run:
	python manage.py runserver

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

shell:
	python manage.py shell

test:
	python manage.py test

collectstatic:
	python manage.py collectstatic --noinput