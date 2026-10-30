CREATE TABLE IF NOT EXISTS equipamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    descricao TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('Caminhão', 'Máquina', 'Equipamento')),
    marca TEXT,
    modelo TEXT,
    ano INTEGER,
    placa_serie TEXT,
    unidade_medida TEXT NOT NULL CHECK (unidade_medida IN ('km', 'h')),
    leitura_atual REAL NOT NULL DEFAULT 0,
    intervalo_troca REAL NOT NULL,
    intervalo_dias INTEGER,
    oleo_recomendado TEXT,
    capacidade_litros REAL,
    observacoes TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mecanicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    matricula TEXT NOT NULL UNIQUE,
    telefone TEXT,
    especialidade TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trocas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipamento_id INTEGER NOT NULL REFERENCES equipamentos (id),
    mecanico_id INTEGER NOT NULL REFERENCES mecanicos (id),
    data TEXT NOT NULL,
    leitura REAL NOT NULL,
    tipo_oleo TEXT NOT NULL,
    quantidade_litros REAL NOT NULL,
    filtro_oleo INTEGER NOT NULL DEFAULT 0,
    filtro_ar INTEGER NOT NULL DEFAULT 0,
    filtro_combustivel INTEGER NOT NULL DEFAULT 0,
    proxima_leitura REAL NOT NULL,
    proxima_data TEXT,
    observacoes TEXT,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trocas_equipamento ON trocas (equipamento_id, data);
CREATE INDEX IF NOT EXISTS idx_trocas_mecanico ON trocas (mecanico_id);
