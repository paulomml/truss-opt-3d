"""
Funções de consulta utilitárias para os modelos ORM.

Centraliza as leituras mais comuns para que os endpoints e o otimizador
não precisem manipular sessões SQLAlchemy diretamente.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.modelos import Material, Perfil


def listar_materiais_ativos(sessao: Session) -> List[Material]:
    """Retorna todos os materiais ativos, ordenados por nome."""
    stmt = select(Material).where(Material.ativo.is_(True)).order_by(Material.nome)
    return list(sessao.scalars(stmt))


def listar_perfis_ativos(sessao: Session) -> List[Perfil]:
    """Retorna todos os perfis ativos, ordenados por família e nome."""
    stmt = (
        select(Perfil)
        .where(Perfil.ativo.is_(True))
        .order_by(Perfil.familia, Perfil.nome)
    )
    return list(sessao.scalars(stmt))


def buscar_material_por_nome(sessao: Session, nome: str) -> Optional[Material]:
    """Busca um material pelo nome (case-sensitive)."""
    stmt = select(Material).where(Material.nome == nome)
    return sessao.scalars(stmt).first()


def buscar_perfil_por_nome(sessao: Session, nome: str) -> Optional[Perfil]:
    """Busca um perfil pelo nome (case-sensitive)."""
    stmt = select(Perfil).where(Perfil.nome == nome)
    return sessao.scalars(stmt).first()


def listar_perfis_por_familia(sessao: Session, familia: str) -> List[Perfil]:
    """Lista perfis de uma família específica (ex.: 'RHS')."""
    stmt = (
        select(Perfil)
        .where(Perfil.ativo.is_(True), Perfil.familia == familia)
        .order_by(Perfil.nome)
    )
    return list(sessao.scalars(stmt))


def listar_perfis_por_uso(sessao: Session, uso: str) -> List[Perfil]:
    """Lista perfis cujo uso recomendado contém o termo (ex.: 'Banzo')."""
    stmt = (
        select(Perfil)
        .where(
            Perfil.ativo.is_(True),
            Perfil.uso_recomendado.ilike(f"%{uso}%"),
        )
        .order_by(Perfil.nome)
    )
    return list(sessao.scalars(stmt))
