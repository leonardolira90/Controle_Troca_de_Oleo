import re

import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({
        "TESTING": True, "DATABASE": str(tmp_path / "teste.sqlite"),
        "ADMIN_LOGIN": "admin", "ADMIN_SENHA": "senha-segura",
    })


def token(cliente, url="/login"):
    return re.search(r'name="csrf_token" value="([^"]+)"', cliente.get(url).get_data(as_text=True)).group(1)


def entrar(cliente, login="admin", senha="senha-segura"):
    return cliente.post("/login", data={"login": login, "senha": senha, "csrf_token": token(cliente)})


def test_paginas_exigem_login(app):
    cliente = app.test_client()
    for url in ["/", "/equipamentos/", "/mecanicos/", "/trocas/", "/usuarios", "/backup"]:
        resposta = cliente.get(url)
        assert resposta.status_code == 302
        assert resposta.headers["Location"].startswith("/login")


def test_login_e_logout(app):
    cliente = app.test_client()
    assert "incorretos" in entrar(cliente, senha="errada").get_data(as_text=True)
    assert entrar(cliente).status_code == 302
    assert cliente.get("/").status_code == 200
    cliente.post("/logout", data={"csrf_token": token(cliente, "/")})
    assert cliente.get("/").status_code == 302


def test_login_redireciona_para_pagina_pedida(app):
    cliente = app.test_client()
    resposta = cliente.post("/login?proximo=/mecanicos/", data={"login": "admin", "senha": "senha-segura", "csrf_token": token(cliente)})
    assert resposta.headers["Location"] == "/mecanicos/"


def test_post_sem_csrf_e_rejeitado(app):
    cliente = app.test_client()
    entrar(cliente)
    resposta = cliente.post("/mecanicos/novo", data={"nome": "X", "matricula": "1"})
    assert resposta.status_code == 400


def test_admin_cria_usuario_comum_sem_acesso_admin(app):
    cliente = app.test_client()
    entrar(cliente)
    dados = {"nome": "Operador", "login": "op", "senha": "12345678", "confirmacao": "12345678", "csrf_token": token(cliente, "/")}
    assert "Usuário criado" in cliente.post("/usuarios", data=dados, follow_redirects=True).get_data(as_text=True)

    outro = app.test_client()
    entrar(outro, "op", "12345678")
    assert outro.get("/").status_code == 200
    assert outro.get("/usuarios").status_code == 403
    assert outro.get("/backup").status_code == 403


def test_senha_curta_e_recusada(app):
    cliente = app.test_client()
    entrar(cliente)
    dados = {"nome": "Op", "login": "op", "senha": "123", "confirmacao": "123", "csrf_token": token(cliente, "/")}
    assert "pelo menos 8" in cliente.post("/usuarios", data=dados, follow_redirects=True).get_data(as_text=True)


def test_backup_baixa_banco_sqlite(app):
    cliente = app.test_client()
    entrar(cliente)
    resposta = cliente.get("/backup")
    assert resposta.status_code == 200
    assert resposta.data.startswith(b"SQLite format 3")


def test_comando_criar_admin(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "cli.sqlite")})
    resultado = app.test_cli_runner().invoke(args=["criar-admin", "--login", "chefe", "--nome", "Chefe", "--senha", "senha-forte"])
    assert "criado" in resultado.output
    cliente = app.test_client()
    assert entrar(cliente, "chefe", "senha-forte").status_code == 302
