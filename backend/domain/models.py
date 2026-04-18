from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# Definição das abstrações do domínio estrutural.
# Estes modelos representam a topologia, as condições de contorno e os resultados da análise matricial.


class RawNode(BaseModel):
    # Representação vetorial do nó no espaço R³.
    id: str
    x: float
    y: float
    z: float
    support: str = "None"  # Condição de vinculação (Livre, Engastado, Elástico).


class RawMember(BaseModel):
    # Elemento finito unidimensional (barra) definido pela incidência nodal.
    id: int
    node_start: str
    node_end: str
    group: Optional[str] = "Padrão"


class RawTruss(BaseModel):
    # Conjunto topológico que define a malha estrutural completa.
    nodes: Dict[str, RawNode]
    members: List[RawMember]


class TrussRequest(BaseModel):
    # Parâmetros de entrada para o design paramétrico da treliça Howe.
    length: float = Field(
        ..., gt=0, description="Vão livre (L) da estrutura em metros."
    )
    height: float = Field(
        ..., gt=0, description="Altura máxima (H) ou flecha da treliça."
    )
    width: float = Field(..., ge=0, description="Largura da seção transversal (W).")
    divisions: int = Field(
        ..., ge=2, description="Número de painéis ou subdivisões do vão."
    )
    total_load: float = Field(
        ..., gt=0, description="Carga vertical total solicitante em kgf."
    )
    soil_type: str = Field(
        "Rocha", description="Classificação geotécnica para interação solo-estrutura."
    )
    custom_ks: Optional[float] = Field(
        None, description="Coeficiente de reação do subleito definido pelo usuário."
    )
    footing_b: float = Field(0.6, gt=0, description="Dimensão B da base da fundação.")
    footing_l: float = Field(0.6, gt=0, description="Dimensão L da base da fundação.")
    raw_truss: Optional[RawTruss] = None


class NodeResult(BaseModel):
    # Resultados nodais obtidos após a convergência do equilíbrio estático.
    id: str
    x: float
    y: float
    z: float
    support: str = "None"


class MemberResult(BaseModel):
    # Resumo do estado de tensão e utilização de cada elemento de barra.
    id: int
    node_start: str
    node_end: str
    group: str
    profile: str
    axial_force: float  # Esforço axial de cálculo em Newtons (N).
    utilization: (
        float  # Taxa de aproveitamento da seção (U = Solicitação / Resistência).
    )
    stress_type: str  # Classificação do esforço preponderante (Tração ou Compressão).


class OptimizationResponse(BaseModel):
    # Resposta final do processo de otimização econômica e técnica.
    is_structurally_stable: bool  # Flag de atendimento aos Estados Limites (ELU/ELS).
    status_message: str
    total_weight: float  # Massa total da estrutura otimizada.
    total_cost: float = (
        0.0  # Custo financeiro estimado baseado no mercado de aços estruturais.
    )
    winning_material: str = (
        "N/A"  # Material que apresentou o melhor desempenho de custo.
    )
    members: List[MemberResult]
    nodes: Dict[str, NodeResult]
