from flask import Blueprint, render_template

from ..db import get_db
from ..manutencao import PROXIMA, SEM_REGISTRO, VENCIDA, painel

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    db = get_db()
    itens = painel(db)
    resumo = {
        "equipamentos": len(itens),
        "vencidas": sum(1 for i in itens if i["status"] == VENCIDA),
        "proximas": sum(1 for i in itens if i["status"] == PROXIMA),
        "sem_registro": sum(1 for i in itens if i["status"] == SEM_REGISTRO),
        "mecanicos": db.execute("SELECT COUNT(*) FROM mecanicos WHERE ativo = 1").fetchone()[0],
    }
    recentes = db.execute(
        """SELECT t.*, e.codigo, e.descricao, e.unidade_medida, m.nome AS mecanico
           FROM trocas t
           JOIN equipamentos e ON e.id = t.equipamento_id
           JOIN mecanicos m ON m.id = t.mecanico_id
           ORDER BY t.data DESC, t.id DESC LIMIT 10"""
    ).fetchall()
    return render_template("index.html", itens=itens, resumo=resumo, recentes=recentes)
