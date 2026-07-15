"""
Verificações NBR 8800:2008 — Projeto de estruturas de aço.

Implementa:
- Esbeltez máxima (Item 5.2.8 e 5.3.4)
- Flambagem local — Fator Q (Anexo F)
- Força axial resistente N_rd (Item 5.2.2 e 5.3.2)
- Fator de redução χ (Item 5.3.3)
- Momento fletor resistente M_rd (regime elástico)
- Interação N + M (Item 5.5.1.2)
- Estado Limite de Serviço — Flecha (ELS)

Referências diretas às equações da norma são mantidas nos comentários.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from engineering.modelos_fisicos import BarraFisica, MaterialFisico, PerfilFisico


# Coeficiente de ponderação γ_a1 para combinações normais (NBR 8800 Tabela 4).
GAMMA_A1 = 1.10


@dataclass
class ResultadoVerificacao:
    """Resultado consolidado das verificações normativas de uma barra."""
    utilization: float
    n_rd: float
    m_rd: float
    esbeltez: float
    fator_chi: float
    fator_q: float
    violacao_normativa: bool
    detalhes: str


def calcular_fator_q(perfil: PerfilFisico, material: MaterialFisico) -> float:
    """
    Fator de redução total associado à flambagem local (Anexo F).

    Para perfis L/RHS/Ue formados a frio, a esbeltez local b/t determina
    a necessidade de redução da área efetiva. Implementação simplificada
    mas conservadora: Qs = 1.0 se b/t ≤ λr; senão Qa = Ae/Ag.
    """
    t = max(perfil.t_mm, 0.1) / 1000.0  # em metros
    # Largura da mesa mais esbelta (conservador): bf ou h.
    b_mm = max(perfil.h_mm, perfil.bf_mm)
    b = b_mm / 1000.0
    # Largura flat descontando dobras (≈ 3t de cada lado).
    b_flat = max(b - 6 * t, t)

    # λr = 1.40 * sqrt(E/fy) para elementos sem enrijecedor longitudinal.
    e_pa = material.e_pa
    fy_pa = material.fy_pa
    lamb_r = 1.40 * math.sqrt(e_pa / fy_pa)
    lamb = b_flat / t

    if lamb <= lamb_r:
        return 1.0

    # Largura efetiva (Anexo F, Eq. F.3 — versão simplificada).
    bef = (
        1.92
        * t
        * math.sqrt(e_pa / fy_pa)
        * (1.0 - (0.38 / lamb) * math.sqrt(e_pa / fy_pa))
    )
    bef = min(bef, b_flat)
    a_ef = perfil.area_m2 - 4 * (b_flat - bef) * t
    q_a = max(a_ef / perfil.area_m2, 0.001)
    return q_a


def calcular_fator_chi(
    perfil: PerfilFisico,
    material: MaterialFisico,
    lkx: float,
    lky: float,
    fator_q: float,
) -> tuple[float, float, float]:
    """
    Fator de redução χ associado à flambagem global (Item 5.3.3).

    Retorna (chi, lambda0, esbeltez_maxima).
    """
    e_pa = material.e_pa
    fy_pa = material.fy_pa * fator_q  # fy reduzido por Q
    a = perfil.area_m2

    # Força axial de flambagem elástica Ne (Anexo E) — menor entre eixos.
    n_ex = (math.pi**2 * e_pa * perfil.ix_m4) / (lkx**2)
    n_ey = (math.pi**2 * e_pa * perfil.iy_m4) / (lky**2)
    n_e = min(n_ex, n_ey)

    if n_e <= 0:
        return 0.0, float("inf"), float("inf")

    # λ0 = sqrt(Ag * Q * fy / Ne)  (Item 5.3.3.2)
    lambda_0 = math.sqrt((a * fy_pa) / n_e)

    # χ (Item 5.3.3.1).
    if lambda_0 <= 1.5:
        chi = 0.658 ** (lambda_0**2)
    else:
        chi = 0.877 / (lambda_0**2)

    # Esbeltez física (L/r).
    r_x = perfil.raio_giracao_x
    r_y = perfil.raio_giracao_y
    esb_x = lkx / r_x if r_x > 0 else float("inf")
    esb_y = lky / r_y if r_y > 0 else float("inf")
    esbeltez_max = max(esb_x, esb_y)

    return chi, lambda_0, esbeltez_max


def calcular_n_rd(
    perfil: PerfilFisico,
    material: MaterialFisico,
    fator_chi: float,
    fator_q: float,
    tracao: bool = False,
) -> float:
    """
    Força axial resistente de cálculo N_rd (Item 5.2.2 / 5.3.2).

    - Tração: N_rd = A · fy / γa1
    - Compressão: N_rd = χ · Q · A · fy / γa1
    """
    a = perfil.area_m2
    fy = material.fy_pa
    if tracao:
        return a * fy / GAMMA_A1
    return fator_chi * fator_q * a * fy / GAMMA_A1


def calcular_m_rd(
    perfil: PerfilFisico,
    material: MaterialFisico,
) -> tuple[float, float]:
    """
    Momento fletor resistente de cálculo M_rd (regime elástico).

    Retorna (M_rd_z, M_rd_y) em torno dos eixos forte (Z) e fraco (Y).
    W = I / (c/2), onde c é a dimensão da seção na direção do momento.
    """
    fy = material.fy_pa
    # Módulo resistente elástico W = I / (c/2).
    c_z = max(perfil.h_mm, 1.0) / 1000.0  # altura
    c_y = max(perfil.bf_mm, 1.0) / 1000.0  # largura
    w_z = perfil.ix_m4 / (c_z / 2) if c_z > 0 else 0.0
    w_y = perfil.iy_m4 / (c_y / 2) if c_y > 0 else 0.0
    m_rd_z = w_z * fy / GAMMA_A1
    m_rd_y = w_y * fy / GAMMA_A1
    return m_rd_z, m_rd_y


def verificar_barra_nbr8800(
    barra: BarraFisica,
    perfil: PerfilFisico,
    material: MaterialFisico,
    lkx: Optional[float] = None,
    lky: Optional[float] = None,
) -> ResultadoVerificacao:
    """
    Executa todas as verificações NBR 8800 para uma barra.

    Retorna a taxa de utilização U e os parâmetros normativos.
    U > 1.0 indica violação.
    """
    comprimento = barra.length
    lkx = lkx if lkx is not None else comprimento
    lky = lky if lky is not None else comprimento

    # Força axial (convenção: tração > 0, compressão < 0).
    n_sd = abs(barra.axial_force)
    tracao = barra.axial_force >= -0.01

    # 1) Fator Q (flambagem local).
    fator_q = calcular_fator_q(perfil, material)

    # 2) Fator χ e esbeltez.
    chi, lambda_0, esbeltez_max = calcular_fator_chi(
        perfil, material, lkx, lky, fator_q
    )

    # 3) Limites de esbeltez.
    if not tracao and esbeltez_max > 200.0:
        return ResultadoVerificacao(
            utilization=999.0,
            n_rd=0.0, m_rd=0.0,
            esbeltez=esbeltez_max,
            fator_chi=chi, fator_q=fator_q,
            violacao_normativa=True,
            detalhes=f"Esbeltez {esbeltez_max:.0f} > 200 (compressão, NBR 8800 5.3.4.1).",
        )
    if tracao and esbeltez_max > 300.0:
        return ResultadoVerificacao(
            utilization=999.0,
            n_rd=0.0, m_rd=0.0,
            esbeltez=esbeltez_max,
            fator_chi=chi, fator_q=fator_q,
            violacao_normativa=True,
            detalhes=f"Esbeltez {esbeltez_max:.0f} > 300 (tração, NBR 8800 5.2.8.1).",
        )

    # 4) N_rd e M_rd.
    n_rd = calcular_n_rd(perfil, material, chi, fator_q, tracao=tracao)
    m_rd_z, m_rd_y = calcular_m_rd(perfil, material)
    m_rd = max(m_rd_z, m_rd_y)

    if n_rd <= 0:
        return ResultadoVerificacao(
            utilization=999.0,
            n_rd=0.0, m_rd=m_rd,
            esbeltez=esbeltez_max,
            fator_chi=chi, fator_q=fator_q,
            violacao_normativa=True,
            detalhes="N_rd nulo — instabilidade.",
        )

    # 5) Interação N + M (Item 5.5.1.2).
    ratio_n = n_sd / n_rd
    m_sd = abs(barra.mz) + abs(barra.my)
    ratio_m = 0.0
    if m_rd > 0:
        ratio_m = m_sd / m_rd

    if ratio_n >= 0.2:
        utilization = ratio_n + (8.0 / 9.0) * ratio_m
        eq_ref = "NBR 8800 5.5.1.2-a (N/N_rd ≥ 0.2)"
    else:
        utilization = (ratio_n / 2.0) + ratio_m
        eq_ref = "NBR 8800 5.5.1.2-b (N/N_rd < 0.2)"

    violacao = utilization > 1.0
    detalhes = (
        f"{eq_ref} | N_sd={n_sd/1000:.2f} kN, N_rd={n_rd/1000:.2f} kN, "
        f"M_sd={m_sd/1000:.2f} kN·m, M_rd={m_rd/1000:.2f} kN·m, "
        f"χ={chi:.3f}, Q={fator_q:.3f}, λ₀={lambda_0:.2f}, λ={esbeltez_max:.0f}."
    )

    return ResultadoVerificacao(
        utilization=utilization,
        n_rd=n_rd,
        m_rd=m_rd,
        esbeltez=esbeltez_max,
        fator_chi=chi,
        fator_q=fator_q,
        violacao_normativa=violacao,
        detalhes=detalhes,
    )


def verificar_flecha_els(
    flecha_maxima: float,
    vano_real: float,
    limite_divisor: float = 250.0,
) -> tuple[bool, float, str]:
    """
    Verifica o Estado Limite de Serviço (flecha).

    NBR 8800 (e NBR 6120) recomendam L/250 para sobrecargas variáveis.
    Retorna (atendido, flecha_limite, mensagem).
    """
    if vano_real <= 0:
        return True, 0.0, "Vão indefinido — ELS não aplicável."

    flecha_limite = vano_real / limite_divisor
    if flecha_maxima > flecha_limite:
        return (
            False,
            flecha_limite,
            f"Flecha {flecha_maxima*1000:.2f} mm > L/{limite_divisor:.0f} "
            f"({flecha_limite*1000:.2f} mm) — ELS violado.",
        )
    return True, flecha_limite, f"Flecha {flecha_maxima*1000:.2f} mm ≤ L/{limite_divisor:.0f} — ELS atendido."
