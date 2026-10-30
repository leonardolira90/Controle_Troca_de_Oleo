"""Auxiliares simples para ler e validar campos de formulário."""


def destino_local(valor, padrao):
    """Aceita apenas caminhos internos para evitar redirecionamentos externos."""
    if valor and valor.startswith("/") and not valor.startswith("//") and "\\" not in valor:
        return valor
    return padrao


class Formulario:
    def __init__(self, dados):
        self.dados = dados
        self.erros = []

    def texto(self, campo, rotulo, obrigatorio=False):
        valor = (self.dados.get(campo) or "").strip()
        if obrigatorio and not valor:
            self.erros.append(f"{rotulo} é obrigatório.")
        return valor or None

    def numero(self, campo, rotulo, obrigatorio=False, inteiro=False, minimo=None):
        bruto = (self.dados.get(campo) or "").strip().replace(",", ".")
        if not bruto:
            if obrigatorio:
                self.erros.append(f"{rotulo} é obrigatório.")
            return None
        try:
            valor = int(bruto) if inteiro else float(bruto)
        except ValueError:
            self.erros.append(f"{rotulo} deve ser um número válido.")
            return None
        if minimo is not None and valor < minimo:
            self.erros.append(f"{rotulo} deve ser maior ou igual a {minimo}.")
            return None
        return valor

    def opcao(self, campo, rotulo, opcoes):
        valor = self.dados.get(campo)
        if valor not in opcoes:
            self.erros.append(f"{rotulo} inválido.")
            return None
        return valor

    def marcado(self, campo):
        return 1 if self.dados.get(campo) else 0

    @property
    def valido(self):
        return not self.erros
