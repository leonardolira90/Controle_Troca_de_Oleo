# Controle de Troca de Óleo

Sistema web para controlar as trocas de óleo de **caminhões, máquinas e equipamentos**.

## Funcionalidades

- **Cadastro de equipamentos** – código/frota, descrição, tipo (Caminhão, Máquina ou
  Equipamento), marca, modelo, ano, placa/nº de série, óleo recomendado e capacidade do cárter.
  - Cada equipamento é controlado por **quilometragem (km)** ou **horímetro (horas)**.
  - Plano de troca: intervalo em km/horas e, opcionalmente, intervalo máximo em dias
    (a troca vence pelo que ocorrer primeiro).
  - Atualização rápida da leitura atual (km/horímetro).
  - Desativação de equipamentos fora de operação.
- **Cadastro de mecânicos** – nome, matrícula, telefone, especialidade e situação (ativo/inativo),
  com contagem de trocas realizadas por cada um.
- **Registro de trocas de óleo** – equipamento, mecânico responsável, data, leitura no momento
  da troca, tipo e quantidade de óleo, filtros trocados (óleo, ar, combustível) e observações.
  - A próxima troca (leitura e data) é calculada automaticamente.
  - A leitura atual do equipamento é atualizada ao registrar a troca.
- **Painel** com a situação de toda a frota:
  - 🔴 **Vencida** – passou da leitura ou da data prevista;
  - 🟡 **Próxima** – faltam 10% do intervalo ou 7 dias ou menos;
  - 🟢 **Em dia**;
  - ⚪ **Sem registro** – equipamento ainda sem troca registrada.
- **Histórico** de trocas por equipamento e listagem geral com filtros por equipamento,
  mecânico e período, incluindo o total de litros utilizados.
- **Login de usuários** – todas as páginas exigem login. Administradores cadastram outros
  usuários, redefinem senhas e baixam o **backup** do banco de dados (menu do usuário, no topo).

Cadastros com trocas registradas não podem ser excluídos (para preservar o histórico) —
nesses casos, desative o equipamento ou mecânico.

## Tecnologias

- Python 3.10+ e [Flask](https://flask.palletsprojects.com/)
- Banco de dados SQLite (criado automaticamente em `instance/troca_oleo.sqlite`)

## Como executar no computador

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask --app wsgi criar-admin     # cria o primeiro usuário (pede login, nome e senha)
python run.py
```

Acesse <http://127.0.0.1:5000> e entre com o usuário criado.

Variáveis de ambiente opcionais:

| Variável                | Descrição                                                        | Padrão                       |
|-------------------------|------------------------------------------------------------------|------------------------------|
| `DATABASE`              | Caminho do arquivo SQLite                                        | `instance/troca_oleo.sqlite` |
| `SECRET_KEY`            | Chave das sessões de login                                       | gerada automaticamente e salva em `secret_key`, ao lado do banco |
| `ADMIN_LOGIN` / `ADMIN_SENHA` | Cria este administrador na inicialização, se ainda não houver usuários | — |
| `SESSION_COOKIE_SECURE` | `1` para só enviar o cookie de login por HTTPS (use em produção) | desativado                   |
| `PROXY_FIX`             | `1` quando o app roda atrás de um proxy reverso (Fly.io, Railway, Render, nginx) | desativado |
| `HOST`/`PORT`           | Endereço e porta do `run.py`                                     | `127.0.0.1` / `5000`         |
| `FLASK_DEBUG`           | `1` para modo de depuração (nunca em produção)                   | desativado                   |

Para acessar de outros computadores da rede local, use `HOST=0.0.0.0 python run.py`.

## Hospedagem

O sistema usa um único arquivo SQLite, então **o servidor precisa de armazenamento em disco
persistente** — em serviços com disco temporário (por exemplo, o plano gratuito do Render) os
dados seriam apagados a cada reinício. Qualquer que seja a opção, baixe o backup
periodicamente pelo menu **Administrador → Baixar backup**.

### Opção 1 — PythonAnywhere (mais simples, tem plano gratuito)

1. Crie uma conta em <https://www.pythonanywhere.com>. O endereço será
   `https://SEU_USUARIO.pythonanywhere.com`.
2. Abra um console **Bash** (aba *Consoles*) e rode:
   ```bash
   git clone https://github.com/leonardolira90/Controle_Troca_de_Oleo.git
   cd Controle_Troca_de_Oleo
   mkvirtualenv troca --python=python3.12
   pip install -r requirements.txt
   flask --app wsgi criar-admin
   ```
   Se o repositório for privado, o GitHub pedirá usuário e um *Personal Access Token* no lugar da senha.
3. Na aba **Web**: *Add a new web app* → *Manual configuration* → Python 3.12.
4. Ainda na aba **Web**:
   - **Virtualenv**: `/home/SEU_USUARIO/.virtualenvs/troca`
   - **Static files**: URL `/static/` → diretório `/home/SEU_USUARIO/Controle_Troca_de_Oleo/app/static`
   - **Force HTTPS**: ativado
   - Clique no link do **WSGI configuration file** e substitua todo o conteúdo por:
     ```python
     import os, sys
     projeto = "/home/SEU_USUARIO/Controle_Troca_de_Oleo"
     sys.path.insert(0, projeto)
     os.chdir(projeto)
     os.environ["SESSION_COOKIE_SECURE"] = "1"
     from wsgi import application
     ```
5. Clique em **Reload** e acesse o endereço.

Para atualizar depois de mudanças no código: `cd ~/Controle_Troca_de_Oleo && git pull &&
workon troca && pip install -r requirements.txt`, e **Reload** na aba Web. No plano gratuito,
o PythonAnywhere pede que você entre periodicamente na aba Web para manter o site ativo.

### Opção 2 — Docker (Fly.io, Railway, Render com disco, servidor próprio/VPS)

O `Dockerfile` já usa o servidor de produção **gunicorn**, guarda o banco em `/data` e ativa
`PROXY_FIX` e `SESSION_COOKIE_SECURE`. Ao configurar o serviço:

- monte um **volume persistente em `/data`**;
- no primeiro deploy, defina `ADMIN_LOGIN` e `ADMIN_SENHA` (pode removê-las depois que o
  administrador for criado e trocar a senha pelo sistema);
- a porta é lida de `PORT` (padrão `8000`).

Teste local:

```bash
docker build -t troca-oleo .
docker run -p 8000:8000 -v troca-dados:/data -e ADMIN_LOGIN=admin -e ADMIN_SENHA=troque-esta-senha troca-oleo
```

Em um servidor próprio sem Docker: `pip install -r requirements.txt` e
`gunicorn --bind 127.0.0.1:8000 --workers 2 wsgi:app`, atrás de um nginx com HTTPS.

## Testes

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Estrutura

```
app/
  __init__.py        # criação da aplicação e filtros de formatação (datas e números no padrão BR)
  db.py              # conexão SQLite
  schema.sql         # tabelas: equipamentos, mecanicos, trocas, usuarios
  manutencao.py      # regras: cálculo da próxima troca e situação (em dia/próxima/vencida)
  routes/            # páginas: login/usuários, painel, equipamentos, mecânicos, trocas
  templates/         # HTML (Jinja2)
  static/style.css
tests/               # testes automatizados (pytest)
run.py               # servidor de desenvolvimento
wsgi.py              # ponto de entrada de produção (gunicorn / PythonAnywhere)
Dockerfile
```
