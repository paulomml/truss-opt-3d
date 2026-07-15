"""
Modelos ORM do TRUSS-OPT 3D: PostgreSQL via SQLAlchemy 2.0.

Estes modelos substituem os antigos materials.csv e profiles.csv,
fornecendo um catálogo relacional consultável pela API e pelo otimizador.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Material(Base):
    """
    Material estrutural (aço) cadastrado no sistema.

    Cada material possui propriedades mecânicas (E, G, nu, fy, fu) e um
    custo por kg (R$/kg) utilizado pelo GA na função objetivo para
    minimizar o custo total da estrutura.
    """
    __tablename__ = "materiais"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    norma_referencia: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Propriedades mecânicas (unidades SI no sistema internacional).
    e_gpa: Mapped[float] = mapped_column(Float, nullable=False, comment="Módulo de Young (GPa)")
    g_gpa: Mapped[float] = mapped_column(Float, nullable=False, comment="Módulo de cisalhamento (GPa)")
    nu: Mapped[float] = mapped_column(Float, nullable=False, comment="Coeficiente de Poisson")
    fy_mpa: Mapped[float] = mapped_column(Float, nullable=False, comment="Tensão de escoamento (MPa)")
    fu_mpa: Mapped[float] = mapped_column(Float, nullable=False, comment="Tensão de ruptura (MPa)")
    rho_kg_m3: Mapped[float] = mapped_column(Float, nullable=False, comment="Massa específica (kg/m³)")
    custo_kg: Mapped[float] = mapped_column(
        Float, nullable=False, default=8.5,
        comment="Custo unitário (R$/kg): utilizado pelo GA na função objetivo para minimizar custo total."
    )

    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    perfis: Mapped[List["Perfil"]] = relationship(
        "Perfil", back_populates="material", cascade="all, delete-orphan"
    )

    def como_dicionario(self) -> dict:
        """Converte para dict no formato esperado pelo solver FEA."""
        return {
            "id": self.id,
            "name": self.nome,
            "fy": self.fy_mpa,
            "fu": self.fu_mpa,
            "E": self.e_gpa,
            "G": self.g_gpa,
            "nu": self.nu,
            "rho": self.rho_kg_m3,
            "cost_kg": self.custo_kg,
            "norma_ref": self.norma_referencia,
        }


class Perfil(Base):
    """
    Perfil estrutural padronizado (L, RHS, Ue, W, etc).

    As propriedades geométricas (A, Ix, Iy, J) são extraídas de catálogos
    de fabricantes nacionais (Gerdau, Villares, Valmont) e usadas diretamente
    pelo solver MEF e pelas verificações de flambagem local (NBR 8800 Anexo F).
    """
    __tablename__ = "perfis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    familia: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="L | RHS | Ue | W | I | T | Cantoneira"
    )

    # Dimensões nominais (mm): utilizadas no cálculo do Fator Q (NBR 8800 Anexo F).
    h_mm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    bf_mm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    d_mm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    t_mm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Propriedades de seção (unidades SI: m^2, m^4).
    area_m2: Mapped[float] = mapped_column(Float, nullable=False)
    ix_m4: Mapped[float] = mapped_column(Float, nullable=False, comment="Inércia em torno do eixo forte X")
    iy_m4: Mapped[float] = mapped_column(Float, nullable=False, comment="Inércia em torno do eixo fraco Y")
    j_m4: Mapped[float] = mapped_column(Float, nullable=False, comment="Momento de inércia à torção")

    # Metadados de uso recomendado (ex.: "Banzo", "Montante/Diagonal").
    uso_recomendado: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    chapa_referencia: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Associação opcional com material (perfil pode ser específico de um aço).
    material_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("materiais.id", ondelete="SET NULL"), nullable=True
    )

    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    material: Mapped[Optional[Material]] = relationship("Material", back_populates="perfis")

    __table_args__ = (
        Index("ix_perfis_familia", "familia"),
        CheckConstraint("area_m2 > 0", name="ck_perfis_area_positiva"),
    )

    def como_dicionario(self) -> dict:
        """Converte para dict no formato esperado pelo solver FEA."""
        return {
            "id": self.id,
            "Name": self.nome,
            "Familia": self.familia,
            "h_mm": self.h_mm,
            "bf_mm": self.bf_mm,
            "d_mm": self.d_mm,
            "t_mm": self.t_mm,
            "Area_m2": self.area_m2,
            "Ix_m4": self.ix_m4,
            "Iy_m4": self.iy_m4,
            "J_m4": self.j_m4,
            "Uso_recomendado": self.uso_recomendado or "",
            "Chapa_referencia": self.chapa_referencia or "",
            "material_id": self.material_id,
        }


class TarefaOtimizacao(Base):
    """
    Registro persistente de uma tarefa de otimização Celery.

    Permite ao frontend consultar status, progresso e resultado final mesmo
    após a conexão WebSocket ter sido fechada.
    """
    __tablename__ = "tarefas_otimizacao"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"),
        primary_key=True, autoincrement=True
    )
    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(128), unique=True, index=True, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), default="PENDENTE", nullable=False, index=True,
        comment="PENDENTE | EM_ANDAMENTO | CONCLUIDO | FALHOU | CANCELADO",
    )
    progresso: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Payload de entrada (JSON serializado).
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Resultado final (JSON serializado da OptimizationResponse).
    resultado_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mensagem_erro: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Logs de progresso em formato texto (acumulados durante a execução).
    logs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    iniciado_em: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finalizado_em: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_tarefas_status_criado", "status", "criado_em"),
    )


class MemorialCalculo(Base):
    """
    Memorial de cálculo gerado para uma tarefa concluída.

    Armazena metadados do PDF/DOCX para download posterior via API.
    """
    __tablename__ = "memoriais_calculo"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"),
        primary_key=True, autoincrement=True
    )
    tarefa_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tarefas_otimizacao.id", ondelete="CASCADE"), nullable=False
    )
    formato: Mapped[str] = mapped_column(String(8), nullable=False, comment="pdf | docx")
    nome_arquivo: Mapped[str] = mapped_column(String(256), nullable=False)
    conteudo_b64: Mapped[str] = mapped_column(Text, nullable=False, comment="Base64 do arquivo")
    tamanho_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("tarefa_id", "formato", name="uq_memorial_tarefa_formato"),
    )
