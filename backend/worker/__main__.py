"""
Entrypoint do Celery worker.

Executado via celery -A core.celery_app worker no container Docker.
"""
from core.celery_app import app_celery

if __name__ == "__main__":
    app_celery.start()
