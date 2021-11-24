from app.__init__ import create_app
import gunicorn

gunicorn app:create_app() --bind=0.0.0.0:8004