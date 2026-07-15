"""
Verificações NBR 6123:1988: Forças devidas ao vento em edificações.

Implementa o modelo de cargas estáticas de vento em coberturas e fechamentos
verticais, com aplicação 3D na treliça.

Fórmulas principais (Item 4):
    Vk = V0 * S1 * S2 * S3               (velocidade característica)
    q   = 0.613 * Vk^2                     (pressão dinâmica, N/m^2)
    F   = (Ce − Ci) * q * A              (força em elemento de área A)
    Fa  = Ca * q * Ae                     (força de arrasto global)

Onde:
    V0 : velocidade básica do vento (mapa isovelocidade, 30-50 m/s no Brasil)
    S1 : fator topográfico (1.0 terreno plano; >1.0 em encostas)
    S2 : fator de rugosidade (0.5-1.5 conforme classe e altura)
    S3 : fator estatístico (1.0 para edifícios comuns, vida útil 50 anos)
    Ce : coeficiente de forma externo (pressão/sucção)
    Ci : coeficiente de forma interno
    Ca : coeficiente de arrasto
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

from engineering.modelos_fisicos import NoFisico


# Densidade do ar ao nível do mar (kg/m^3): NBR 6123 Item 4.1.c.
RHO_AR = 1.225  # kg/m^3


@dataclass
class ForcaVento:
    """Força de vento aplicada em um nó."""
    no_id: str
    direction: str  # 'FX' | 'FY' | 'FZ'
    valor: float  # em Newtons


@dataclass
class ParametrosVento:
    """Parâmetros de vento NBR 6123."""
    v0_mps: float = 40.0  # Velocidade básica (default: região centro-oeste).
    s1: float = 1.0       # Fator topográfico.
    s2: float = 1.0       # Fator de rugosidade.
    s3: float = 1.0       # Fator estatístico.
    direcao_vento_graus: float = 0.0  # Direção do vento (0 = eixo +X).
    ce_externo: float = 0.8      # Coeficiente de pressão externa (sobrepressão).
    ci_interno: float = 0.0      # Coeficiente de pressão interna.
    ca_arrasto: float = 1.3      # Coeficiente de arrasto (treliças 3D).

    @property
    def velocidade_caracteristica(self) -> float:
        """Vk = V0 * S1 * S2 * S3."""
        return self.v0_mps * self.s1 * self.s2 * self.s3

    @property
    def pressao_dinamica(self) -> float:
        """q = 0.613 * Vk^2 (N/m^2)."""
        return 0.613 * self.velocidade_caracteristica**2


def decompor_direcao_vento(direcao_graus: float) -> Tuple[float, float]:
    """
    Decompõe a direção do vento em componentes X e Z (vento horizontal).

    Retorna (fx_unit, fz_unit): vetor unitário horizontal.
    """
    rad = math.radians(direcao_graus)
    return math.cos(rad), math.sin(rad)


def calcular_area_frontal(
    nos: Dict[str, NoFisico],
    direcao_graus: float,
) -> float:
    """
    Calcula a área frontal (área de sombra) da estrutura na direção do vento.

    Ae = projeção ortogonal da edificação sobre um plano perpendicular ao vento.
    """
    if not nos:
        return 0.0

    fx, fz = decompor_direcao_vento(direcao_graus)
    # Coordenadas dos nós projetadas no eixo do vento.
    proj_vento = [fx * n.x + fz * n.z for n in nos.values()]
    if not proj_vento:
        return 0.0
    altura_max = max(n.y for n in nos.values())
    largura_vento = max(proj_vento) - min(proj_vento)
    return altura_max * largura_vento


def calcular_forcas_vento_3d(
    nos: Dict[str, NoFisico],
    parametros: ParametrosVento,
    nos_banzo_superior: List[str],
    nos_fachada: List[str] | None = None,
) -> List[ForcaVento]:
    """
    Modela as forças de vento em 3D sobre a treliça.

    Estratégia:
    1. Para coberturas (banzo superior): aplica pressão vertical (FY)
       combinada com sucção conforme coeficiente Ce.
    2. Para fachadas verticais (montantes de torres): aplica pressão
       horizontal (FX e FZ conforme direção do vento).
    3. Para o conjunto: calcula força de arrasto global e distribui entre
       nós das fachadas perpendiculares ao vento.

    A área tributária de cada nó é estimada a partir da malha: para
    treliças planares, considera-se 1 m de profundidade.
    """
    if not nos:
        return []

    forcas: List[ForcaVento] = []
    q = parametros.pressao_dinamica
    fx_dir, fz_dir = decompor_direcao_vento(parametros.direcao_vento_graus)

    # 1) Sucção/pressão vertical na cobertura (banzo superior).
    if nos_banzo_superior:
        # Área tributária por nó = área total da cobertura / nº de nós.
        # Estimativa da profundidade (z) e vão (x) da cobertura.
        xs = [nos[nid].x for nid in nos_banzo_superior if nid in nos]
        zs = [nos[nid].z for nid in nos_banzo_superior if nid in nos]
        if xs and zs:
            area_cobertura = (max(xs) - min(xs)) * (max(zs) - min(zs))
            area_por_no = area_cobertura / len(nos_banzo_superior)
            # Força vertical: (Ce - Ci) * q * A: sinal negativo (sucção para cima).
            forca_vertical = (parametros.ce_externo - parametros.ci_interno) * q * area_por_no
            for nid in nos_banzo_superior:
                if nid in nos:
                    forcas.append(ForcaVento(
                        no_id=nid,
                        direction="FY",
                        valor=-abs(forca_vertical),  # Sucção para cima.
                    ))

    # 2) Pressão horizontal nas fachadas (montantes de torres).
    if nos_fachada:
        # Area frontal estimada por nó.
        area_frontal = calcular_area_frontal(nos, parametros.direcao_vento_graus)
        if area_frontal > 0 and nos_fachada:
            area_por_no = area_frontal / len(nos_fachada)
            forca_horizontal = (parametros.ce_externo - parametros.ci_interno) * q * area_por_no
            for nid in nos_fachada:
                if nid in nos:
                    # Componente X (na direção do vento).
                    forcas.append(ForcaVento(
                        no_id=nid,
                        direction="FX",
                        valor=forca_horizontal * fx_dir,
                    ))
                    # Componente Z (perpendicular).
                    forcas.append(ForcaVento(
                        no_id=nid,
                        direction="FZ",
                        valor=forca_horizontal * fz_dir,
                    ))

    # 3) Arrasto global aplicado nos nós do plano perpendicular.
    area_arrasto = calcular_area_frontal(nos, parametros.direcao_vento_graus)
    if area_arrasto > 0:
        forca_arrasto = parametros.ca_arrasto * q * area_arrasto
        # Distribui igualmente entre todos os nós (aproximação conservadora).
        if nos:
            por_no = forca_arrasto / max(len(nos), 1)
            for nid in nos:
                forcas.append(ForcaVento(
                    no_id=nid,
                    direction="FX",
                    valor=por_no * fx_dir,
                ))
                forcas.append(ForcaVento(
                    no_id=nid,
                    direction="FZ",
                    valor=por_no * fz_dir,
                ))

    return forcas


def identificar_fachadas_perpendiculares(
    nos: Dict[str, NoFisico],
    direcao_graus: float,
) -> List[str]:
    """
    Identifica os nós pertencentes às fachadas perpendiculares à direção do vento.

    Para vento no eixo X (0 graus), as fachadas são as faces em x_min e x_max.
    """
    if not nos:
        return []
    fx, fz = decompor_direcao_vento(direcao_graus)
    proj = {nid: fx * n.x + fz * n.z for nid, n in nos.items()}
    if not proj:
        return []
    p_min = min(proj.values())
    p_max = max(proj.values())
    # Tolerância de 5% da largura.
    tol = 0.05 * (p_max - p_min) if p_max > p_min else 0.1
    fachadas = [
        nid for nid, p in proj.items()
        if abs(p - p_min) < tol or abs(p - p_max) < tol
    ]
    return fachadas
