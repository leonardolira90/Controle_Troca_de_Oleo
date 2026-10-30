import os
from datetime import date, datetime

from flask import Flask


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao"),
        DATABASE=os.environ.get(
            "DATABASE", os.path.join(app.instance_path, "troca_oleo.sqlite")
        ),
    )
    if config:
        app.config.update(config)
    os.makedirs(app.instance_path, exist_ok=True)

    from . import db
    db.init_app(app)

    from .routes import equipamentos, main, mecanicos, trocas
    app.register_blueprint(main.bp)
    app.register_blueprint(equipamentos.bp)
    app.register_blueprint(mecanicos.bp)
    app.register_blueprint(trocas.bp)

    app.jinja_env.filters["data_br"] = data_br
    app.jinja_env.filters["numero"] = numero
    return app


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
