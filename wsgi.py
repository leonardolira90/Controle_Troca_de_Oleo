"""Ponto de entrada WSGI para servidores de produção (gunicorn, PythonAnywhere etc.)."""
from app import create_app

application = app = create_app()
