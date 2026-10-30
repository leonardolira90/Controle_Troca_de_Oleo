import sqlite3

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..db import get_db
from ..manutencao import situacao, ultima_troca
from .forms import Formulario, destino_local

bp = Blueprint("equipamentos", __name__, url_prefix="/equipamentos")

TIPOS = ["Caminhão", "Máquina", "Equipamento"]
UNIDADES = {"km": "Quilometragem (km)", "h": "Horímetro (horas)"}


def buscar(equipamento_id):
    eq = get_db().execute(
        "SELECT * FROM equipamentos WHERE id = ?", (equipamento_id,)
    ).fetchone()
    if eq is None:
        abort(404)
    return eq


def ler_formulario(dados):
    f = Formulario(dados)
    valores = {
        "codigo": f.texto("codigo", "Código", obrigatorio=True),
        "descricao": f.texto("descricao", "Descrição", obrigatorio=True),
        "tipo": f.opcao("tipo", "Tipo", TIPOS),
        "marca": f.texto("marca", "Marca"),
        "modelo": f.texto("modelo", "Modelo"),
        "ano": f.numero("ano", "Ano", inteiro=True, minimo=1900),
        "placa_serie": f.texto("placa_serie", "Placa / Nº de série"),
        "unidade_medida": f.opcao("unidade_medida", "Unidade de medição", UNIDADES),
        "leitura_atual": f.numero("leitura_atual", "Leitura atual", minimo=0) or 0,
        "intervalo_troca": f.numero("intervalo_troca", "Intervalo de troca", obrigatorio=True, minimo=1),
        "intervalo_dias": f.numero("intervalo_dias", "Intervalo em dias", inteiro=True, minimo=1),
        "oleo_recomendado": f.texto("oleo_recomendado", "Óleo recomendado"),
        "capacidade_litros": f.numero("capacidade_litros", "Capacidade do cárter", minimo=0),
        "observacoes": f.texto("observacoes", "Observações"),
        "ativo": f.marcado("ativo"),
    }
    return f, valores


@bp.route("/")
def lista():
    db = get_db()
    busca = request.args.get("q", "").strip()
    tipo = request.args.get("tipo", "")
    sql = "SELECT * FROM equipamentos WHERE 1 = 1"
    params = []
    if busca:
        sql += " AND (codigo LIKE ? OR descricao LIKE ? OR placa_serie LIKE ? OR modelo LIKE ?)"
        params += [f"%{busca}%"] * 4
    if tipo in TIPOS:
        sql += " AND tipo = ?"
        params.append(tipo)
    itens = []
    for eq in db.execute(sql + " ORDER BY ativo DESC, codigo", params).fetchall():
        itens.append({"equipamento": eq, **situacao(eq, ultima_troca(db, eq["id"]))})
    return render_template(
        "equipamentos/lista.html", itens=itens, tipos=TIPOS, busca=busca, tipo=tipo
    )


@bp.route("/novo", methods=["GET", "POST"])
def novo():
    valores = {"ativo": 1, "unidade_medida": "km", "tipo": "Caminhão"}
    if request.method == "POST":
        f, valores = ler_formulario(request.form)
        if f.valido:
            try:
                db = get_db()
                cur = db.execute(
                    f"INSERT INTO equipamentos ({', '.join(valores)}) VALUES ({', '.join('?' * len(valores))})",
                    list(valores.values()),
                )
                db.commit()
                flash("Equipamento cadastrado com sucesso.", "sucesso")
                return redirect(url_for(".detalhe", equipamento_id=cur.lastrowid))
            except sqlite3.IntegrityError:
                f.erros.append("Já existe um equipamento com este código.")
        for erro in f.erros:
            flash(erro, "erro")
    return render_template(
        "equipamentos/form.html", eq=valores, tipos=TIPOS, unidades=UNIDADES, titulo="Novo equipamento"
    )


@bp.route("/<int:equipamento_id>")
def detalhe(equipamento_id):
    db = get_db()
    eq = buscar(equipamento_id)
    historico = db.execute(
        """SELECT t.*, m.nome AS mecanico FROM trocas t
           JOIN mecanicos m ON m.id = t.mecanico_id
           WHERE t.equipamento_id = ? ORDER BY t.data DESC, t.leitura DESC, t.id DESC""",
        (equipamento_id,),
    ).fetchall()
    ultima = historico[0] if historico else None
    return render_template(
        "equipamentos/detalhe.html",
        eq=eq,
        historico=historico,
        ultima=ultima,
        unidades=UNIDADES,
        **situacao(eq, ultima),
    )


@bp.route("/<int:equipamento_id>/editar", methods=["GET", "POST"])
def editar(equipamento_id):
    eq = buscar(equipamento_id)
    valores = dict(eq)
    if request.method == "POST":
        f, valores = ler_formulario(request.form)
        if f.valido:
            try:
                db = get_db()
                db.execute(
                    f"UPDATE equipamentos SET {', '.join(f'{c} = ?' for c in valores)} WHERE id = ?",
                    [*valores.values(), equipamento_id],
                )
                db.commit()
                flash("Equipamento atualizado.", "sucesso")
                return redirect(url_for(".detalhe", equipamento_id=equipamento_id))
            except sqlite3.IntegrityError:
                f.erros.append("Já existe um equipamento com este código.")
        for erro in f.erros:
            flash(erro, "erro")
        valores["id"] = equipamento_id
    return render_template(
        "equipamentos/form.html", eq=valores, tipos=TIPOS, unidades=UNIDADES, titulo=f"Editar {eq['codigo']}"
    )


@bp.route("/<int:equipamento_id>/leitura", methods=["POST"])
def atualizar_leitura(equipamento_id):
    eq = buscar(equipamento_id)
    f = Formulario(request.form)
    leitura = f.numero("leitura_atual", "Leitura atual", obrigatorio=True, minimo=0)
    if f.valido and leitura < eq["leitura_atual"]:
        f.erros.append("A nova leitura não pode ser menor que a leitura atual.")
    if f.valido:
        db = get_db()
        db.execute("UPDATE equipamentos SET leitura_atual = ? WHERE id = ?", (leitura, equipamento_id))
        db.commit()
        flash("Leitura atualizada.", "sucesso")
    for erro in f.erros:
        flash(erro, "erro")
    return redirect(destino_local(request.form.get("voltar"), url_for(".detalhe", equipamento_id=equipamento_id)))


@bp.route("/<int:equipamento_id>/excluir", methods=["POST"])
def excluir(equipamento_id):
    buscar(equipamento_id)
    db = get_db()
    possui_trocas = db.execute(
        "SELECT 1 FROM trocas WHERE equipamento_id = ? LIMIT 1", (equipamento_id,)
    ).fetchone()
    if possui_trocas:
        flash("Este equipamento possui trocas registradas. Desative-o em vez de excluir.", "erro")
        return redirect(url_for(".detalhe", equipamento_id=equipamento_id))
    db.execute("DELETE FROM equipamentos WHERE id = ?", (equipamento_id,))
    db.commit()
    flash("Equipamento excluído.", "sucesso")
    return redirect(url_for(".lista"))
