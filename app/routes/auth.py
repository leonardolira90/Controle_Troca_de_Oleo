import hmac
import secrets
import sqlite3
from functools import wraps

import click
from flask import (
    Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for,
)
from flask.cli import with_appcontext
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import get_db
from .forms import Formulario, destino_local

bp = Blueprint("auth", __name__)

SENHA_MINIMA = 8
PUBLICAS = {"auth.login", "static"}


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


@bp.before_app_request
def carregar_usuario_e_proteger():
    g.usuario = None
    usuario_id = session.get("usuario_id")
    if usuario_id is not None:
        g.usuario = get_db().execute(
            "SELECT * FROM usuarios WHERE id = ? AND ativo = 1", (usuario_id,)
        ).fetchone()
        if g.usuario is None:
            session.clear()

    if request.method == "POST" and current_app.config.get("CSRF", True):
        enviado = request.form.get("csrf_token", "")
        esperado = session.get("csrf_token", "")
        if not esperado or not hmac.compare_digest(enviado, esperado):
            abort(400, "Formulário expirado. Recarregue a página e tente novamente.")

    if g.usuario is None and request.endpoint not in PUBLICAS:
        return redirect(url_for("auth.login", proximo=request.full_path.rstrip("?")))


def admin_obrigatorio(view):
    @wraps(view)
    def envolvida(*args, **kwargs):
        if not g.usuario["admin"]:
            abort(403)
        return view(*args, **kwargs)
    return envolvida


def validar_senha(f, campo="senha", confirmacao="confirmacao"):
    senha = f.dados.get(campo) or ""
    if len(senha) < SENHA_MINIMA:
        f.erros.append(f"A senha deve ter pelo menos {SENHA_MINIMA} caracteres.")
    elif senha != f.dados.get(confirmacao):
        f.erros.append("A confirmação não confere com a senha.")
    return senha


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.usuario is not None:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        usuario = get_db().execute(
            "SELECT * FROM usuarios WHERE login = ? AND ativo = 1",
            ((request.form.get("login") or "").strip(),),
        ).fetchone()
        if usuario and check_password_hash(usuario["senha_hash"], request.form.get("senha", "")):
            session.clear()
            session["usuario_id"] = usuario["id"]
            session.permanent = True
            return redirect(destino_local(request.args.get("proximo"), url_for("main.index")))
        flash("Usuário ou senha incorretos.", "erro")
    return render_template("auth/login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/senha", methods=["GET", "POST"])
def alterar_senha():
    if request.method == "POST":
        f = Formulario(request.form)
        if not check_password_hash(g.usuario["senha_hash"], request.form.get("atual", "")):
            f.erros.append("Senha atual incorreta.")
        senha = validar_senha(f)
        if f.valido:
            db = get_db()
            db.execute(
                "UPDATE usuarios SET senha_hash = ? WHERE id = ?",
                (generate_password_hash(senha), g.usuario["id"]),
            )
            db.commit()
            flash("Senha alterada.", "sucesso")
            return redirect(url_for("main.index"))
        for erro in f.erros:
            flash(erro, "erro")
    return render_template("auth/senha.html")


@bp.route("/usuarios", methods=["GET", "POST"])
@admin_obrigatorio
def usuarios():
    db = get_db()
    valores = {}
    if request.method == "POST":
        f = Formulario(request.form)
        valores = {
            "nome": f.texto("nome", "Nome", obrigatorio=True),
            "login": f.texto("login", "Usuário", obrigatorio=True),
            "admin": f.marcado("admin"),
        }
        senha = validar_senha(f)
        if f.valido:
            try:
                db.execute(
                    "INSERT INTO usuarios (nome, login, senha_hash, admin) VALUES (?, ?, ?, ?)",
                    (valores["nome"], valores["login"], generate_password_hash(senha), valores["admin"]),
                )
                db.commit()
                flash("Usuário criado.", "sucesso")
                return redirect(url_for(".usuarios"))
            except sqlite3.IntegrityError:
                f.erros.append("Já existe um usuário com este login.")
        for erro in f.erros:
            flash(erro, "erro")
    lista = db.execute("SELECT * FROM usuarios ORDER BY ativo DESC, nome").fetchall()
    return render_template("auth/usuarios.html", usuarios=lista, u=valores)


@bp.route("/usuarios/<int:usuario_id>/ativo", methods=["POST"])
@admin_obrigatorio
def alternar_ativo(usuario_id):
    if usuario_id == g.usuario["id"]:
        flash("Você não pode desativar o próprio usuário.", "erro")
    else:
        db = get_db()
        db.execute("UPDATE usuarios SET ativo = 1 - ativo WHERE id = ?", (usuario_id,))
        db.commit()
        flash("Situação do usuário alterada.", "sucesso")
    return redirect(url_for(".usuarios"))


@bp.route("/usuarios/<int:usuario_id>/senha", methods=["POST"])
@admin_obrigatorio
def redefinir_senha(usuario_id):
    f = Formulario(request.form)
    senha = validar_senha(f)
    if f.valido:
        db = get_db()
        db.execute(
            "UPDATE usuarios SET senha_hash = ? WHERE id = ?", (generate_password_hash(senha), usuario_id)
        )
        db.commit()
        flash("Senha redefinida.", "sucesso")
    for erro in f.erros:
        flash(erro, "erro")
    return redirect(url_for(".usuarios"))


def criar_usuario(nome, login, senha, admin=True):
    db = get_db()
    db.execute(
        "INSERT INTO usuarios (nome, login, senha_hash, admin) VALUES (?, ?, ?, ?)",
        (nome, login, generate_password_hash(senha), 1 if admin else 0),
    )
    db.commit()


def criar_admin_inicial(app):
    """Cria o administrador a partir de ADMIN_LOGIN/ADMIN_SENHA se ainda não houver usuários."""
    login, senha = app.config.get("ADMIN_LOGIN"), app.config.get("ADMIN_SENHA")
    if not login or not senha:
        return
    with app.app_context():
        if get_db().execute("SELECT 1 FROM usuarios LIMIT 1").fetchone() is None:
            try:
                criar_usuario("Administrador", login, senha)
            except sqlite3.IntegrityError:
                pass  # outro processo do servidor criou ao mesmo tempo


@click.command("criar-admin")
@click.option("--login", prompt="Login")
@click.option("--nome", prompt="Nome", default="Administrador")
@click.password_option("--senha", prompt="Senha")
@with_appcontext
def criar_admin_comando(login, nome, senha):
    """Cria um usuário administrador."""
    if len(senha) < SENHA_MINIMA:
        raise click.BadParameter(f"a senha deve ter pelo menos {SENHA_MINIMA} caracteres.")
    try:
        criar_usuario(nome, login, senha)
    except sqlite3.IntegrityError:
        raise click.ClickException("já existe um usuário com este login.")
    click.echo(f"Administrador '{login}' criado.")
