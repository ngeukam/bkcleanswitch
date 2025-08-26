# cleanswitch/__init__.py
from cleanswitch.celery import app as celery_app

__all__ = ('celery_app',)