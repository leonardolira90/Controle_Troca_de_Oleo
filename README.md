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

Cadastros com trocas registradas não podem ser excluídos (para preservar o histórico) —
nesses casos, desative o equipamento ou mecânico.

## Tecnologias

- Python 3.10+ e [Flask](https://flask.palletsprojects.com/)
- Banco de dados SQLite (criado automaticamente em `instance/troca_oleo.sqlite`)

## Como executar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Acesse <http://127.0.0.1:5000>.

Variáveis de ambiente opcionais:

| Variável      | Descrição                                   | Padrão                         |
|---------------|---------------------------------------------|--------------------------------|
| `DATABASE`    | Caminho do arquivo SQLite                   | `instance/troca_oleo.sqlite`   |
| `SECRET_KEY`  | Chave de sessão do Flask (defina em produção) | valor de desenvolvimento     |
| `HOST`/`PORT` | Endereço e porta do servidor                | `127.0.0.1` / `5000`           |
| `FLASK_DEBUG` | `1` para modo de depuração                  | desativado                     |

Para acessar de outros computadores da rede, use `HOST=0.0.0.0 python run.py`.

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
  schema.sql         # tabelas: equipamentos, mecanicos, trocas
  manutencao.py      # regras: cálculo da próxima troca e situação (em dia/próxima/vencida)
  routes/            # páginas: painel, equipamentos, mecânicos, trocas
  templates/         # HTML (Jinja2)
  static/style.css
tests/               # testes automatizados (pytest)
run.py               # ponto de entrada
```
