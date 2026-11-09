"""Ordem das seções do notebook."""
from secoes_final import secoes_final
from secoes_inicio import secoes_inicio
from secoes_metodos import secoes_metodos


def SECOES(codigo_modulo):
    return secoes_inicio(codigo_modulo) + secoes_metodos(codigo_modulo) + secoes_final()
