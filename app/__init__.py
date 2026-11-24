import os
import secrets
from datetime import date, datetime, timedelta

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    app.config.update(
        DATABASE=os.environ.get(
            "DATABASE", os.path.join(app.instance_path, "troca_oleo.sqlite")
        ),
        ADMIN_LOGIN=os.environ.get("ADMIN_LOGIN"),
        ADMIN_SENHA=os.environ.get("ADMIN_SENHA"),
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    )
    if config:
        app.config.update(config)
    pasta_dados = os.path.dirname(os.path.abspath(app.config["DATABASE"]))
    os.makedirs(pasta_dados, exist_ok=True)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or chave_secreta(pasta_dados)
    if os.environ.get("PROXY_FIX") == "1":
        # Atrás de um proxy reverso (Render, Railway, Fly.io, nginx...).
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    from . import db
    db.init_app(app)

    from .routes import auth, equipamentos, main, mecanicos, trocas
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(equipamentos.bp)
    app.register_blueprint(mecanicos.bp)
    app.register_blueprint(trocas.bp)
    app.cli.add_command(auth.criar_admin_comando)
    auth.criar_admin_inicial(app)

    app.jinja_env.globals["csrf_token"] = auth.csrf_token
    app.jinja_env.filters["data_br"] = data_br
    app.jinja_env.filters["numero"] = numero
    return app


def chave_secreta(pasta):
    """Gera uma SECRET_KEY aleatória na primeira execução e a guarda junto ao banco de dados."""
    caminho = os.path.join(pasta, "secret_key")
    if not os.path.exists(caminho):
        # Grava num arquivo temporário e cria o definitivo de forma atômica, para que
        # vários processos do servidor iniciando juntos acabem usando a mesma chave.
        temporario = f"{caminho}.{os.getpid()}"
        with open(os.open(temporario, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as arquivo:
            arquivo.write(secrets.token_hex(32))
        try:
            os.link(temporario, caminho)
        except FileExistsError:
            pass
        finally:
            os.remove(temporario)
    with open(caminho, encoding="utf-8") as arquivo:
        return arquivo.read().strip()


def data_br(valor):
    """Formata 'AAAA-MM-DD' (ou date) como 'DD/MM/AAAA'."""
    if not valor:
        return "—"
    if isinstance(valor, str):
        try:
            valor = datetime.strptime(valor[:10], "%Y-%m-%d").date()
        except ValueError:
            return valor
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    return valor


def numero(valor, casas=0):
    """Formata números no padrão brasileiro (1.234,5)."""
    if valor is None or valor == "":
        return "—"
    texto = f"{float(valor):,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")
