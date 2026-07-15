"""
Modelos físicos do domínio estrutural (distinctes dos Pydantic schemas).

Estes dataclasses são usados internamente pelo solver e pelos verificadores
normativos. São mutáveis e otimizados para performance (sem overhead Pydantic
em loops internos do GA).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class NoFisico:
    """Nó estrutural com coordenadas cartesianas."""
    id: str
    x: float
    y: float
    z: float
    support: str = "None"  # Pinned | Roller | Fixed | None


@dataclass
class BarraFisica:
    """Barra estrutural conectando dois nós."""
    id: int
    node_start: str
    node_end: str
    group: str
    length: float
    profile_name: str = ""
    area: float = 0.0
    ix: float = 0.0
    iy: float = 0.0
    j: float = 0.0
    # Resultados pós-análise (preenchidos pelo solver).
    axial_force: float = 0.0
    my: float = 0.0
    mz: float = 0.0
    utilization: float = 0.0
    stress_type: str = "Tração"
    # Propriedades derivadas para NBR 8800.
    n_rd: float = 0.0
    m_rd: float = 0.0
    esbeltez: float = 0.0
    fator_chi: float = 1.0
    fator_q: float = 1.0
    lkx: float = 0.0
    lky: float = 0.0


@dataclass
class MaterialFisico:
    """Material estrutural com propriedades mecânicas."""
    nome: str
    e_gpa: float
    g_gpa: float
    nu: float
    fy_mpa: float
    fu_mpa: float
    rho_kg_m3: float
    custo_kg: float = 8.5
    norma_ref: Optional[str] = None

    @property
    def e_pa(self) -> float:
        """Módulo de Young em Pascal."""
        return self.e_gpa * 1e9

    @property
    def g_pa(self) -> float:
        """Módulo de cisalhamento em Pascal."""
        return self.g_gpa * 1e9

    @property
    def fy_pa(self) -> float:
        """Tensão de escoamento em Pascal."""
        return self.fy_mpa * 1e6

    @property
    def fu_pa(self) -> float:
        """Tensão de ruptura em Pascal."""
        return self.fu_mpa * 1e6


@dataclass
class PerfilFisico:
    """Perfil estrutural padronizado."""
    id: int
    nome: str
    familia: str
    h_mm: float
    bf_mm: float
    d_mm: float
    t_mm: float
    area_m2: float
    ix_m4: float
    iy_m4: float
    j_m4: float
    uso_recomendado: str = ""
    chapa_referencia: str = ""

    @property
    def raio_giracao_x(self) -> float:
        """Raio de giração em torno do eixo forte X."""
        return (self.ix_m4 / self.area_m2) ** 0.5 if self.area_m2 > 0 else 0.0

    @property
    def raio_giracao_y(self) -> float:
        """Raio de giração em torno do eixo fraco Y."""
        return (self.iy_m4 / self.area_m2) ** 0.5 if self.area_m2 > 0 else 0.0


@dataclass
class ResultadoAnalise:
    """Resultado completo de uma análise MEF."""
    barras: List[BarraFisica] = field(default_factory=list)
    nos: Dict[str, NoFisico] = field(default_factory=dict)
    peso_total_kg: float = 0.0
    flecha_maxima: float = 0.0
    vano_real: float = 0.0
    contraflecha: float = 0.0
    utilizacao_maxima: float = 0.0
    erro: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    # Deslocamentos nodais para visualização.
    deslocamentos: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)


def perfil_dict_para_fisico(dados: dict) -> PerfilFisico:
    """Converte um dict (do ORM ou CSV) para PerfilFisico."""
    return PerfilFisico(
        id=dados.get("id", 0),
        nome=dados["Name"] if "Name" in dados else dados["nome"],
        familia=dados.get("Familia", dados.get("familia", "L")),
        h_mm=float(dados.get("h_mm", 0.0)),
        bf_mm=float(dados.get("bf_mm", 0.0)),
        d_mm=float(dados.get("d_mm", 0.0)),
        t_mm=float(dados.get("t_mm", 0.0)),
        area_m2=float(dados.get("Area_m2", dados.get("area_m2", 0.0))),
        ix_m4=float(dados.get("Ix_m4", dados.get("ix_m4", 0.0))),
        iy_m4=float(dados.get("Iy_m4", dados.get("iy_m4", 0.0))),
        j_m4=float(dados.get("J_m4", dados.get("j_m4", 0.0))),
        uso_recomendado=dados.get("Uso_recomendado", dados.get("uso_recomendado", "")),
        chapa_referencia=dados.get("Chapa_referencia", dados.get("chapa_referencia", "")),
    )


def material_dict_para_fisico(dados: dict) -> MaterialFisico:
    """Converte um dict (do ORM) para MaterialFisico."""
    return MaterialFisico(
        nome=dados["name"] if "name" in dados else dados["nome"],
        e_gpa=float(dados.get("E", dados.get("e_gpa", 200.0))),
        g_gpa=float(dados.get("G", dados.get("g_gpa", 76.9))),
        nu=float(dados.get("nu", 0.30)),
        fy_mpa=float(dados.get("fy", dados.get("fy_mpa", 250.0))),
        fu_mpa=float(dados.get("fu", dados.get("fu_mpa", 400.0))),
        rho_kg_m3=float(dados.get("rho", dados.get("rho_kg_m3", 7850.0))),
        custo_kg=float(dados.get("cost_kg", dados.get("custo_kg", 8.5))),
        norma_ref=dados.get("norma_ref", dados.get("norma_referencia")),
    )
