from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# Definição das abstrações do domínio estrutural.
# Estes modelos representam a estrutura, os apoios e os resultados da análise.


class RawNode(BaseModel):
    id: str
    x: float
    y: float
    z: float
    support: str = "None"


class RawMember(BaseModel):
    id: int
    node_start: str
    node_end: str
    group: Optional[str] = "Padrão"


class RawTruss(BaseModel):
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
        ..., ge=0, description="Carga vertical total solicitante em kgf."
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
    id: str
    x: float
    y: float
    z: float
    support: str = "None"


class MemberResult(BaseModel):
    id: int
    node_start: str
    node_end: str
    group: str
    profile: str
    axial_force: float
    utilization: float
    stress_type: str


class OptimizationResponse(BaseModel):
    is_structurally_stable: bool
    status_message: str
    total_weight: float
    total_cost: float = 0.0
    winning_material: str = "N/A"
    members: List[MemberResult]
    nodes: Dict[str, NodeResult]
