"""
Pacote de banco de dados: modelos ORM, sessão e utilitários de consulta.
"""
from db.modelos import (
    Material,
    Perfil,
    TarefaOtimizacao,
    MemorialCalculo,
)
from db.consultas import (
    listar_materiais_ativos,
    listar_perfis_ativos,
    buscar_material_por_nome,
    buscar_perfil_por_nome,
    listar_perfis_por_familia,
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
