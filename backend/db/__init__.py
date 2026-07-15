"""
Pacote de banco de dados: modelos ORM, sessão e utilitários de consulta.
"""

from db.consultas import (
    buscar_material_por_nome,
    buscar_perfil_por_nome,
    listar_materiais_ativos,
    listar_perfis_ativos,
    listar_perfis_por_familia,
)
from db.modelos import (
    Material,
    MemorialCalculo,
    Perfil,
    TarefaOtimizacao,
)

__all__ = [
    "Material",
    "Perfil",
    "TarefaOtimizacao",
    "MemorialCalculo",
    "listar_materiais_ativos",
    "listar_perfis_ativos",
    "buscar_material_por_nome",
    "buscar_perfil_por_nome",
    "listar_perfis_por_familia",
]
