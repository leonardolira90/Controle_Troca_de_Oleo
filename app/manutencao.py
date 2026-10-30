"""Regras de negócio: cálculo da próxima troca e situação de cada equipamento."""
from datetime import date, datetime, timedelta

# Margens para considerar a troca "próxima" do vencimento.
MARGEM_PERCENTUAL = 0.10
MARGEM_DIAS = 7

EM_DIA = "Em dia"
PROXIMA = "Próxima"
VENCIDA = "Vencida"
SEM_REGISTRO = "Sem registro"


def calcular_proxima(leitura, data_troca, intervalo_troca, intervalo_dias):
    proxima_leitura = leitura + intervalo_troca
    proxima_data = None
    if intervalo_dias:
        proxima_data = (data_troca + timedelta(days=intervalo_dias)).isoformat()
    return proxima_leitura, proxima_data


def situacao(equipamento, ultima_troca, hoje=None):
    """Retorna um dict com a situação de troca de óleo do equipamento.

    A troca vence pelo que ocorrer primeiro: leitura (km/horas) ou data.
    """
    hoje = hoje or date.today()
    if ultima_troca is None:
        return {"status": SEM_REGISTRO, "restante": None, "dias_restantes": None}

    restante = ultima_troca["proxima_leitura"] - equipamento["leitura_atual"]
    dias_restantes = None
    if ultima_troca["proxima_data"]:
        proxima_data = datetime.strptime(ultima_troca["proxima_data"], "%Y-%m-%d").date()
        dias_restantes = (proxima_data - hoje).days

    if restante <= 0 or (dias_restantes is not None and dias_restantes <= 0):
        status = VENCIDA
    elif restante <= equipamento["intervalo_troca"] * MARGEM_PERCENTUAL or (
        dias_restantes is not None and dias_restantes <= MARGEM_DIAS
    ):
        status = PROXIMA
    else:
        status = EM_DIA
    return {"status": status, "restante": restante, "dias_restantes": dias_restantes}


def ultima_troca(db, equipamento_id):
    return db.execute(
        "SELECT * FROM trocas WHERE equipamento_id = ? ORDER BY data DESC, leitura DESC, id DESC LIMIT 1",
        (equipamento_id,),
    ).fetchone()


def painel(db, incluir_inativos=False):
    """Lista equipamentos com a situação de troca, mais urgentes primeiro."""
    sql = "SELECT * FROM equipamentos"
    if not incluir_inativos:
        sql += " WHERE ativo = 1"
    itens = []
    for eq in db.execute(sql + " ORDER BY codigo").fetchall():
        ultima = ultima_troca(db, eq["id"])
        itens.append({"equipamento": eq, "ultima": ultima, **situacao(eq, ultima)})
    ordem = {VENCIDA: 0, PROXIMA: 1, SEM_REGISTRO: 2, EM_DIA: 3}
    itens.sort(key=lambda i: ordem[i["status"]])
    return itens
