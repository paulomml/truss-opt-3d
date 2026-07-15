"""
Pacote de verificações normativas modulares.

Cada norma vive em seu próprio módulo:
- nbr_8800.py: Estruturas de aço (ELU, ELS, flambagem).
- nbr_6120.py: Ações em edificações (cargas, assimetrias, combinações).
- nbr_6123.py: Vento em edificações (pressão dinâmica, arrasto).
"""
from engineering.standards.nbr_8800 import (
    ResultadoVerificacao,
    calcular_fator_chi,
    calcular_fator_q,
    calcular_m_rd,
    calcular_n_rd,
    verificar_barra_nbr8800,
    verificar_flecha_els,
)
from engineering.standards.nbr_6120 import (
    calcular_carga_cobertura,
    combinacoes_elu,
    combinacoes_els,
    gerar_casos_assimetricos,
    gerar_casos_manutencao,
    verificar_empozamento,
)
from engineering.standards.nbr_6123 import (
    ForcaVento,
    ParametrosVento,
    calcular_area_frontal,
    calcular_forcas_vento_3d,
    decompor_direcao_vento,
    identificar_fachadas_perpendiculares,
)

__all__ = [
    "ResultadoVerificacao",
    "calcular_fator_chi",
    "calcular_fator_q",
    "calcular_m_rd",
    "calcular_n_rd",
    "verificar_barra_nbr8800",
    "verificar_flecha_els",
    "calcular_carga_cobertura",
    "combinacoes_elu",
    "combinacoes_els",
    "gerar_casos_assimetricos",
    "gerar_casos_manutencao",
    "verificar_empozamento",
    "ForcaVento",
    "ParametrosVento",
    "calcular_area_frontal",
    "calcular_forcas_vento_3d",
    "decompor_direcao_vento",
    "identificar_fachadas_perpendiculares",
]
