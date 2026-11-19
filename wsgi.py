"""gunicorn 入口：gunicorn ... wsgi:app"""

from app import app

__all__ = ["app"]