import sqlite3

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..db import get_db
from .forms import Formulario

bp = Blueprint("mecanicos", __name__, url_prefix="/mecanicos")


def buscar(mecanico_id):
    mec = get_db().execute("SELECT * FROM mecanicos WHERE id = ?", (mecanico_id,)).fetchone()
    if mec is None:
        abort(404)
    return mec


def ler_formulario(dados):
    f = Formulario(dados)
    valores = {
        "nome": f.texto("nome", "Nome", obrigatorio=True),
        "matricula": f.texto("matricula", "Matrícula", obrigatorio=True),
        "telefone": f.texto("telefone", "Telefone"),
        "especialidade": f.texto("especialidade", "Especialidade"),
        "ativo": f.marcado("ativo"),
    }
    return f, valores


@bp.route("/")
def lista():
    mecanicos = get_db().execute(
        """SELECT m.*, COUNT(t.id) AS total_trocas, MAX(t.data) AS ultima_troca
           FROM mecanicos m LEFT JOIN trocas t ON t.mecanico_id = m.id
           GROUP BY m.id ORDER BY m.ativo DESC, m.nome"""
    ).fetchall()
    return render_template("mecanicos/lista.html", mecanicos=mecanicos)


@bp.route("/novo", methods=["GET", "POST"])
def novo():
    valores = {"ativo": 1}
    if request.method == "POST":
        f, valores = ler_formulario(request.form)
        if f.valido:
            try:
                db = get_db()
                db.execute(
                    "INSERT INTO mecanicos (nome, matricula, telefone, especialidade, ativo) VALUES (?, ?, ?, ?, ?)",
                    list(valores.values()),
                )
                db.commit()
                flash("Mecânico cadastrado com sucesso.", "sucesso")
                return redirect(url_for(".lista"))
            except sqlite3.IntegrityError:
                f.erros.append("Já existe um mecânico com esta matrícula.")
        for erro in f.erros:
            flash(erro, "erro")
    return render_template("mecanicos/form.html", mec=valores, titulo="Novo mecânico")


@bp.route("/<int:mecanico_id>/editar", methods=["GET", "POST"])
def editar(mecanico_id):
    mec = buscar(mecanico_id)
    valores = dict(mec)
    if request.method == "POST":
        f, valores = ler_formulario(request.form)
        if f.valido:
            try:
                db = get_db()
                db.execute(
                    "UPDATE mecanicos SET nome = ?, matricula = ?, telefone = ?, especialidade = ?, ativo = ? WHERE id = ?",
                    [*valores.values(), mecanico_id],
                )
                db.commit()
                flash("Mecânico atualizado.", "sucesso")
                return redirect(url_for(".lista"))
            except sqlite3.IntegrityError:
                f.erros.append("Já existe um mecânico com esta matrícula.")
        for erro in f.erros:
            flash(erro, "erro")
        valores["id"] = mecanico_id
    return render_template("mecanicos/form.html", mec=valores, titulo=f"Editar {mec['nome']}")


@bp.route("/<int:mecanico_id>/excluir", methods=["POST"])
def excluir(mecanico_id):
    buscar(mecanico_id)
    db = get_db()
    if db.execute("SELECT 1 FROM trocas WHERE mecanico_id = ? LIMIT 1", (mecanico_id,)).fetchone():
        flash("Este mecânico possui trocas registradas. Desative-o em vez de excluir.", "erro")
    else:
        db.execute("DELETE FROM mecanicos WHERE id = ?", (mecanico_id,))
        db.commit()
        flash("Mecânico excluído.", "sucesso")
    return redirect(url_for(".lista"))
