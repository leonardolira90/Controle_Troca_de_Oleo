from datetime import date, timedelta

import pytest

from app import create_app
from app.db import get_db
from app.manutencao import EM_DIA, PROXIMA, SEM_REGISTRO, VENCIDA, situacao


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "teste.sqlite")})


@pytest.fixture
def client(app):
    return app.test_client()


def cadastrar_equipamento(client, **extra):
    dados = {
        "codigo": "CAM-001", "descricao": "Caminhão basculante", "tipo": "Caminhão",
        "unidade_medida": "km", "leitura_atual": "50000", "intervalo_troca": "10000",
        "intervalo_dias": "180", "oleo_recomendado": "15W40", "capacidade_litros": "28",
        "ativo": "1",
    }
    dados.update(extra)
    return client.post("/equipamentos/novo", data=dados, follow_redirects=True)


def cadastrar_mecanico(client, **extra):
    dados = {"nome": "João da Silva", "matricula": "M001", "telefone": "", "especialidade": "Diesel", "ativo": "1"}
    dados.update(extra)
    return client.post("/mecanicos/novo", data=dados, follow_redirects=True)


def registrar_troca(client, **extra):
    dados = {
        "equipamento_id": "1", "mecanico_id": "1", "data": date.today().isoformat(),
        "leitura": "52000", "tipo_oleo": "15W40", "quantidade_litros": "28", "filtro_oleo": "1",
    }
    dados.update(extra)
    return client.post("/trocas/nova", data=dados, follow_redirects=True)


def test_paginas_abrem_vazias(client):
    for url in ["/", "/equipamentos/", "/equipamentos/novo", "/mecanicos/", "/mecanicos/novo", "/trocas/", "/trocas/nova"]:
        assert client.get(url).status_code == 200, url


def test_cadastro_de_equipamento_e_codigo_duplicado(client):
    resposta = cadastrar_equipamento(client)
    assert "Equipamento cadastrado com sucesso" in resposta.get_data(as_text=True)
    resposta = cadastrar_equipamento(client)
    assert "Já existe um equipamento com este código" in resposta.get_data(as_text=True)


def test_validacao_de_equipamento(client):
    resposta = cadastrar_equipamento(client, codigo="", intervalo_troca="abc")
    texto = resposta.get_data(as_text=True)
    assert "Código é obrigatório" in texto
    assert "Intervalo de troca deve ser um número válido" in texto


def test_cadastro_e_edicao_de_mecanico(client, app):
    assert "Mecânico cadastrado com sucesso" in cadastrar_mecanico(client).get_data(as_text=True)
    client.post("/mecanicos/1/editar", data={"nome": "João Souza", "matricula": "M001"})
    with app.app_context():
        mec = get_db().execute("SELECT * FROM mecanicos WHERE id = 1").fetchone()
    assert mec["nome"] == "João Souza"
    assert mec["ativo"] == 0


def test_registro_de_troca_calcula_proxima_e_atualiza_leitura(client, app):
    cadastrar_equipamento(client)
    cadastrar_mecanico(client)
    resposta = registrar_troca(client)
    assert "Troca registrada" in resposta.get_data(as_text=True)
    with app.app_context():
        db = get_db()
        troca = db.execute("SELECT * FROM trocas").fetchone()
        eq = db.execute("SELECT * FROM equipamentos").fetchone()
    assert troca["proxima_leitura"] == 62000
    assert troca["proxima_data"] == (date.today() + timedelta(days=180)).isoformat()
    assert eq["leitura_atual"] == 52000


def test_troca_exige_equipamento_e_mecanico_ativos(client):
    cadastrar_equipamento(client, ativo="")
    cadastrar_mecanico(client)
    texto = registrar_troca(client).get_data(as_text=True)
    assert "Equipamento não encontrado ou inativo" in texto


def test_troca_nao_aceita_data_futura(client):
    cadastrar_equipamento(client)
    cadastrar_mecanico(client)
    amanha = (date.today() + timedelta(days=1)).isoformat()
    assert "não pode estar no futuro" in registrar_troca(client, data=amanha).get_data(as_text=True)


def test_nao_exclui_cadastros_com_trocas(client):
    cadastrar_equipamento(client)
    cadastrar_mecanico(client)
    registrar_troca(client)
    texto = client.post("/equipamentos/1/excluir", follow_redirects=True).get_data(as_text=True)
    assert "Desative-o em vez de excluir" in texto
    texto = client.post("/mecanicos/1/excluir", follow_redirects=True).get_data(as_text=True)
    assert "Desative-o em vez de excluir" in texto


def test_atualizar_leitura_nao_permite_retroceder(client):
    cadastrar_equipamento(client)
    texto = client.post("/equipamentos/1/leitura", data={"leitura_atual": "100"}, follow_redirects=True).get_data(as_text=True)
    assert "não pode ser menor" in texto


def test_redirecionamento_externo_e_ignorado(client):
    cadastrar_equipamento(client)
    resposta = client.post("/equipamentos/1/leitura", data={"leitura_atual": "60000", "voltar": "//exemplo.com"})
    assert resposta.headers["Location"] == "/equipamentos/1"


def test_painel_mostra_troca_vencida(client):
    cadastrar_equipamento(client)
    cadastrar_mecanico(client)
    registrar_troca(client)
    client.post("/equipamentos/1/leitura", data={"leitura_atual": "63000"})
    texto = client.get("/").get_data(as_text=True)
    assert "selo-vencida" in texto
    assert "1.000 km atrasada" in texto


@pytest.mark.parametrize(
    "leitura_atual, proxima_data, esperado",
    [
        (52000, None, EM_DIA),
        (61500, None, PROXIMA),
        (62000, None, VENCIDA),
        (52000, date(2026, 1, 5), PROXIMA),
        (52000, date(2026, 1, 1), VENCIDA),
    ],
)
def test_situacao(leitura_atual, proxima_data, esperado):
    eq = {"leitura_atual": leitura_atual, "intervalo_troca": 10000}
    troca = {"proxima_leitura": 62000, "proxima_data": proxima_data.isoformat() if proxima_data else None}
    assert situacao(eq, troca, hoje=date(2026, 1, 1))["status"] == esperado


def test_situacao_sem_registro():
    assert situacao({"leitura_atual": 0, "intervalo_troca": 100}, None)["status"] == SEM_REGISTRO
