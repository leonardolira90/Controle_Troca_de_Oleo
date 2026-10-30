from datetime import date, datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..db import get_db
from ..manutencao import calcular_proxima
from .forms import Formulario, destino_local

bp = Blueprint("trocas", __name__, url_prefix="/trocas")


def opcoes(db):
    equipamentos = db.execute(
        "SELECT id, codigo, descricao, unidade_medida, leitura_atual, oleo_recomendado, capacidade_litros "
        "FROM equipamentos WHERE ativo = 1 ORDER BY codigo"
    ).fetchall()
    mecanicos = db.execute(
        "SELECT id, nome, matricula FROM mecanicos WHERE ativo = 1 ORDER BY nome"
    ).fetchall()
    return equipamentos, mecanicos


@bp.route("/")
def lista():
    db = get_db()
    filtros = {
        "equipamento_id": request.args.get("equipamento_id", ""),
        "mecanico_id": request.args.get("mecanico_id", ""),
        "inicio": request.args.get("inicio", ""),
        "fim": request.args.get("fim", ""),
    }
    sql = """SELECT t.*, e.codigo, e.descricao, e.unidade_medida, m.nome AS mecanico
             FROM trocas t
             JOIN equipamentos e ON e.id = t.equipamento_id
             JOIN mecanicos m ON m.id = t.mecanico_id WHERE 1 = 1"""
    params = []
    if filtros["equipamento_id"].isdigit():
        sql += " AND t.equipamento_id = ?"
        params.append(int(filtros["equipamento_id"]))
    if filtros["mecanico_id"].isdigit():
        sql += " AND t.mecanico_id = ?"
        params.append(int(filtros["mecanico_id"]))
    if filtros["inicio"]:
        sql += " AND t.data >= ?"
        params.append(filtros["inicio"])
    if filtros["fim"]:
        sql += " AND t.data <= ?"
        params.append(filtros["fim"])
    trocas = db.execute(sql + " ORDER BY t.data DESC, t.id DESC", params).fetchall()
    total_litros = sum(t["quantidade_litros"] for t in trocas)
    equipamentos = db.execute("SELECT id, codigo, descricao FROM equipamentos ORDER BY codigo").fetchall()
    mecanicos = db.execute("SELECT id, nome FROM mecanicos ORDER BY nome").fetchall()
    return render_template(
        "trocas/lista.html",
        trocas=trocas,
        filtros=filtros,
        equipamentos=equipamentos,
        mecanicos=mecanicos,
        total_litros=total_litros,
    )


@bp.route("/nova", methods=["GET", "POST"])
def nova():
    db = get_db()
    equipamentos, mecanicos = opcoes(db)
    valores = {
        "equipamento_id": request.args.get("equipamento_id", ""),
        "data": date.today().isoformat(),
        "filtro_oleo": 1,
    }
    if request.method == "POST":
        f = Formulario(request.form)
        valores = dict(request.form)
        equipamento_id = f.numero("equipamento_id", "Equipamento", obrigatorio=True, inteiro=True)
        mecanico_id = f.numero("mecanico_id", "Mecânico", obrigatorio=True, inteiro=True)
        data_texto = f.texto("data", "Data da troca", obrigatorio=True)
        leitura = f.numero("leitura", "Leitura (km/horas)", obrigatorio=True, minimo=0)
        tipo_oleo = f.texto("tipo_oleo", "Tipo de óleo", obrigatorio=True)
        quantidade = f.numero("quantidade_litros", "Quantidade (litros)", obrigatorio=True, minimo=0)

        eq = None
        if equipamento_id is not None:
            eq = db.execute(
                "SELECT * FROM equipamentos WHERE id = ? AND ativo = 1", (equipamento_id,)
            ).fetchone()
            if eq is None:
                f.erros.append("Equipamento não encontrado ou inativo.")
        if mecanico_id is not None and not db.execute(
            "SELECT 1 FROM mecanicos WHERE id = ? AND ativo = 1", (mecanico_id,)
        ).fetchone():
            f.erros.append("Mecânico não encontrado ou inativo.")

        data_troca = None
        if data_texto:
            try:
                data_troca = datetime.strptime(data_texto, "%Y-%m-%d").date()
            except ValueError:
                f.erros.append("Data da troca inválida.")
            else:
                if data_troca > date.today():
                    f.erros.append("A data da troca não pode estar no futuro.")

        if f.valido:
            proxima_leitura, proxima_data = calcular_proxima(
                leitura, data_troca, eq["intervalo_troca"], eq["intervalo_dias"]
            )
            cur = db.execute(
                """INSERT INTO trocas (equipamento_id, mecanico_id, data, leitura, tipo_oleo,
                       quantidade_litros, filtro_oleo, filtro_ar, filtro_combustivel,
                       proxima_leitura, proxima_data, observacoes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    equipamento_id, mecanico_id, data_troca.isoformat(), leitura, tipo_oleo,
                    quantidade, f.marcado("filtro_oleo"), f.marcado("filtro_ar"),
                    f.marcado("filtro_combustivel"), proxima_leitura, proxima_data,
                    f.texto("observacoes", "Observações"),
                ),
            )
            if leitura > eq["leitura_atual"]:
                db.execute(
                    "UPDATE equipamentos SET leitura_atual = ? WHERE id = ?", (leitura, equipamento_id)
                )
            db.commit()
            flash(f"Troca registrada (nº {cur.lastrowid}).", "sucesso")
            return redirect(url_for("equipamentos.detalhe", equipamento_id=equipamento_id))
        for erro in f.erros:
            flash(erro, "erro")
    return render_template(
        "trocas/form.html", t=valores, equipamentos=equipamentos, mecanicos=mecanicos
    )


@bp.route("/<int:troca_id>/excluir", methods=["POST"])
def excluir(troca_id):
    db = get_db()
    troca = db.execute("SELECT * FROM trocas WHERE id = ?", (troca_id,)).fetchone()
    if troca is None:
        abort(404)
    db.execute("DELETE FROM trocas WHERE id = ?", (troca_id,))
    db.commit()
    flash("Registro de troca excluído.", "sucesso")
    return redirect(destino_local(request.form.get("voltar"), url_for(".lista")))
