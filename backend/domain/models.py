from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# Definição das abstrações do domínio estrutural.
# Estes modelos representam a estrutura, os apoios e os resultados da análise.


class RawNode(BaseModel):
    """Representação bruta de um nó estrutural vindo do frontend ou gerador."""

    id: str
    x: float
    y: float
    z: float
    support: str = "None"


class RawMember(BaseModel):
    """Representação bruta de uma barra estrutural."""

    id: int
    node_start: str
    node_end: str
    group: Optional[str] = "Padrão"


class RawTruss(BaseModel):
    """Grafo estrutural completo contendo nós e membros."""

    nodes: Dict[str, RawNode]
    members: List[RawMember]


class LoadCase(BaseModel):
    """
    Define um caso de carga vetorial conforme NBR 6120.
    Permite a aplicação de cargas em nós específicos ou rateio automático.
    """

    type: str  # 'G' (Permanente) ou 'Q' (Acidental)
    direction: str  # 'FY', 'FX', 'FZ'
    value: float  # Valor da força (ex: -1500.0)
    nodes: Optional[List[str]] = None  # Se None, ratear entre os nós alvo (ex: banzo superior)


class TrussRequest(BaseModel):
    """Objeto de requisição principal contendo geometria e carregamentos."""

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
    load_cases: List[LoadCase] = Field(
        default_factory=list, description="Lista de casos de carga aplicados."
    )
    soil_type: str = Field(
        "Rocha", description="Classificação geotécnica para interação solo-estrutura."
    )
    water_lamina: float = Field(
        0.0, ge=0, description="Lâmina d'água excepcional para acúmulo (mm). NBR 6120 Item 5.6."
    )
    custom_ks: Optional[float] = Field(
        None, description="Coeficiente de reação do subleito definido pelo usuário."
    )
    footing_b: float = Field(0.6, gt=0, description="Dimensão B da base da fundação.")
    footing_l: float = Field(0.6, gt=0, description="Dimensão L da base da fundação.")
    raw_truss: Optional[RawTruss] = None


class NodeResult(BaseModel):
    """Resultados da análise FEA para um nó individual."""

    id: str
    x: float
    y: float
    z: float
    support: str = "None"


class MemberResult(BaseModel):
    """Resultados do dimensionamento e esforços para uma barra."""

    id: int
    node_start: str
    node_end: str
    group: str
    profile: str
    axial_force: float
    utilization: float
    stress_type: str


class OptimizationResponse(BaseModel):
    """Resposta final do motor de otimização contendo a envoltória de resultados."""

    is_structurally_stable: bool
    status_message: str
    total_weight: float
    total_cost: float = 0.0
    winning_material: str = "N/A"
    precamber: float = 0.0  # Contra-flecha recomendada em metros (Item 10.2 NBR 8800).
    members: List[MemberResult]
    nodes: Dict[str, NodeResult]
