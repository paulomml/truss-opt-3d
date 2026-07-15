"""
Schemas Pydantic para a camada de API.

Estes modelos validam e serializam o tráfego HTTP entre o frontend Nuxt
e o backend FastAPI. São distintos dos modelos ORM (em db/modelos.py)
para manter separação de responsabilidades.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# Geometria e cargas (entrada)
class NoBruto(BaseModel):
    """Nó estrutural enviado pelo frontend."""

    id: str
    x: float
    y: float
    z: float
    support: Literal["Pinned", "Roller", "Fixed", "None"] = "None"


class BarraBruta(BaseModel):
    """Barra estrutural enviada pelo frontend."""

    id: int
    node_start: str
    node_end: str
    group: str | None = "Padrão"


class TrelicaBruta(BaseModel):
    """Grafo estrutural completo (nós + barras)."""

    nodes: dict[str, NoBruto]
    members: list[BarraBruta]


class CasoCarga(BaseModel):
    """
    Caso de carga vetorial conforme NBR 6120.

    - type: 'G' (permanente) ou 'Q' (variável/acidental)
    - direction: 'FX' | 'FY' | 'FZ' | 'MX' | 'MY' | 'MZ'
    - value: valor da força (N) ou momento (N*m)
    - nodes: lista opcional de nós onde aplicar; se None, ratear no banzo superior.
    """

    type: Literal["G", "Q"]
    direction: Literal["FX", "FY", "FZ", "MX", "MY", "MZ"] = "FY"
    value: float
    nodes: list[str] | None = None


class RestricoesOtimizacao(BaseModel):
    """
    Restrições do espaço de busca para o Algoritmo Genético.

    Permite ao usuário limitar manualmente quais perfis/famílias/materiais
    serão considerados, acelerando a convergência e respeitando estoque.
    """

    materiais_permitidos: list[str] | None = Field(
        default=None, description="Lista de nomes de materiais. None = todos."
    )
    familias_permitidas: list[str] | None = Field(
        default=None,
        description="Lista de famílias (L, RHS, Ue, ...). None = todas.",
    )
    perfis_permitidos: list[str] | None = Field(
        default=None,
        description="Lista explícita de nomes de perfis. Sobrepõe familias_permitidas.",
    )
    perfis_excluidos: list[str] | None = Field(
        default=None, description="Perfis explicitamente excluídos do espaço de busca."
    )
    usar_penalidade_diversidade: bool = Field(
        default=True,
        description="Se True, penaliza soluções com muitos perfis distintos.",
    )


class ParametrosVento(BaseModel):
    """
    Parâmetros de vento NBR 6123.

    Se ausente, o otimizador aplica vento padrão (V0=40 m/s, S1=S2=S3=1).
    """

    v0_mps: float = Field(default=40.0, gt=0, description="Velocidade básica do vento (m/s).")
    s1: float = Field(default=1.0, ge=0.6, le=1.5, description="Fator topográfico.")
    s2: float = Field(default=1.0, ge=0.6, le=1.5, description="Fator de rugosidade.")
    s3: float = Field(default=1.0, ge=0.6, le=1.5, description="Fator estatístico.")
    direcao_vento_graus: float = Field(
        default=0.0, ge=0.0, lt=360.0, description="Direção do vento (0 = eixo X)."
    )
    ce_externo: float = Field(default=0.8, description="Coeficiente de pressão externa.")
    ci_interno: float = Field(default=0.0, description="Coeficiente de pressão interna.")


class RequisicaoOtimizacao(BaseModel):
    """Payload principal enviado para /api/otimizar."""

    model_config = ConfigDict(extra="ignore")

    length: float = Field(..., gt=0, description="Vão livre (L) em metros.")
    height: float = Field(..., gt=0, description="Altura máxima (H) em metros.")
    width: float = Field(
        ..., ge=0, description="Largura da seção transversal (W) em metros. 0 = análise 2D."
    )
    divisions: int = Field(..., ge=2, le=50, description="Número de painéis do vão.")
    load_cases: list[CasoCarga] = Field(default_factory=list)
    soil_type: str = Field("Rocha")
    water_lamina: float = Field(0.0, ge=0)
    custom_ks: float | None = None
    footing_b: float = Field(0.6, gt=0)
    footing_l: float = Field(0.6, gt=0)
    raw_truss: TrelicaBruta | None = None

    # Parâmetros de vento NBR 6123.
    parametros_vento: ParametrosVento | None = None

    # Restrições do espaço de busca do GA.
    restricoes: RestricoesOtimizacao | None = None

    # Parâmetros do GA (sobrepõe configurações padrão).
    ag_geracoes: int | None = Field(None, ge=1, le=200)
    ag_populacao: int | None = Field(None, ge=4, le=200)


# Resultados (saída)
class NoResultado(BaseModel):
    """Resultado FEA para um nó."""

    id: str
    x: float
    y: float
    z: float
    support: str = "None"
    deslocamento_y: float = 0.0
    deslocamento_x: float = 0.0
    deslocamento_z: float = 0.0


class BarraResultado(BaseModel):
    """Resultado de dimensionamento para uma barra."""

    id: int
    node_start: str
    node_end: str
    group: str
    profile: str
    material: str = "N/A"
    axial_force: float
    my: float = 0.0
    mz: float = 0.0
    utilization: float
    stress_type: Literal["Tração", "Compressão"]
    n_rd: float = 0.0
    m_rd: float = 0.0
    esbeltez: float = 0.0
    fator_chi: float = 1.0
    fator_q: float = 1.0


class RespostaOtimizacao(BaseModel):
    """Resposta final do motor de otimização."""

    is_structurally_stable: bool
    status_message: str
    total_weight: float
    total_cost: float = 0.0
    winning_material: str = "N/A"
    precamber: float = 0.0
    max_deflection: float = 0.0
    real_span: float = 0.0
    max_utilization: float = 0.0
    num_perfis_distintos: int = 0
    geracoes_executadas: int = 0
    tempo_execucao_segundos: float = 0.0
    members: list[BarraResultado]
    nodes: dict[str, NoResultado]
    logs: list[str] = Field(default_factory=list)


# Status de tarefa assíncrona
class StatusTarefa(BaseModel):
    """Status de uma tarefa Celery consultável por polling."""

    task_id: str
    status: Literal["PENDENTE", "EM_ANDAMENTO", "CONCLUIDO", "FALHOU", "CANCELADO"]
    progresso: float = 0.0
    mensagem: str | None = None
    resultado: RespostaOtimizacao | None = None
    criado_em: datetime | None = None


# Catálogos
class MaterialSchema(BaseModel):
    """Schema público para material."""

    id: int
    nome: str
    norma_referencia: str | None = None
    observacao: str | None = None
    e_gpa: float
    fy_mpa: float
    fu_mpa: float
    rho_kg_m3: float
    custo_kg: float

    model_config = ConfigDict(from_attributes=True)


class PerfilSchema(BaseModel):
    """Schema público para perfil."""

    id: int
    nome: str
    familia: str
    h_mm: float
    bf_mm: float
    t_mm: float
    area_m2: float
    ix_m4: float
    iy_m4: float
    j_m4: float
    uso_recomendado: str | None = None
    chapa_referencia: str | None = None

    model_config = ConfigDict(from_attributes=True)
