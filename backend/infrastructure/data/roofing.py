"""
Utilitário para gestão de pesos nominais de telhados e coberturas.
Referência: NBR 6120:2019 - Ações para o cálculo de estruturas de edificações.
Tabela 5 - Pesos próprios de telhas e componentes.
"""

# Pesos nominais mínimos conforme NBR 6120:2019 Tabela 5.
# Unidades em kN/m2.

ROOFING_WEIGHTS = {
    "Telha Metálica Simples (0.50mm)": 0.06,
    "Telha de Fibrocimento (6mm)": 0.18,
    "Telha Termoacústica (Sanduíche - EPS)": 0.12,
    "Laje de Concreto (e=10cm)": 2.50,
}

def get_roofing_weight(material_name: str) -> float:
    """Retorna o peso próprio em kN/m2 para o material selecionado."""
    return ROOFING_WEIGHTS.get(material_name, 0.0)
