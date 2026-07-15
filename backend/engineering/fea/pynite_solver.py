"""
Solver MEF baseado em PyNite v3.

Responsável por:
1. Construir o modelo FEModel3D a partir do grafo estrutural.
2. Definir materiais, seções, apoios e cargas.
3. Aplicar combinações ELU e ELS (NBR 6120/8681).
4. Aplicar forças de vento NBR 6123.
5. Executar a análise linear e extrair esforços nas barras.
6. Calcular comprimentos de flambagem (Lkx, Lky) para os banzos.
7. Consolidar resultados em ResultadoAnalise.

Notas sobre a API PyNite v3:
- add_section(name, A, Iy, Iz, J): atenção à ordem (Iy, Iz, não Ix).
- add_material(name, E, G, nu, rho, fy=None).
- member.max_moment(direction, combo) onde direction é 'my' ou 'mz'.
- node.DY[combo] é um dict mapeando combo -> deslocamento.
"""

from __future__ import annotations

import contextlib
import logging
import math

from Pynite import FEModel3D

from engineering.modelos_fisicos import (
    BarraFisica,
    MaterialFisico,
    NoFisico,
    PerfilFisico,
    ResultadoAnalise,
)
from engineering.standards.nbr_6123 import (
    ParametrosVento,
    calcular_forcas_vento_3d,
    identificar_fachadas_perpendiculares,
)
from engineering.standards.nbr_8800 import verificar_barra_nbr8800

_logger = logging.getLogger(__name__)


# Coeficiente de reação do subleito (Winkler): NBR 6122 referenciado pela 8800.
# Valores em kN/m^3 (Padrão Terzaghi para placa 0.30x0.30 m).
BANCO_SOLOS = {
    "Areia Fofa": {"ks1": 15000, "tipo": "granular"},
    "Areia Compacta": {"ks1": 100000, "tipo": "granular"},
    "Argila Mole": {"ks1": 10000, "tipo": "coesivo"},
    "Argila Rija": {"ks1": 40000, "tipo": "coesivo"},
    "Rocha": {"ks1": 250000, "tipo": "rigido"},
    "Customizado": {"ks1": 50000, "tipo": "coesivo"},  # fallback
}


def calcular_lk_banzos(
    barras: list[BarraFisica],
    nos: dict[str, NoFisico],
    grupos_banzo: tuple[str, ...] = ("Banzo Superior", "Banzo Inferior"),
    grupos_travamento: tuple[str, ...] = ("Transversal", "Contraventamento"),
) -> dict[int, tuple[float, float]]:
    """
    Mapeia comprimentos de flambagem (Lkx, Lky) para cada barra.

    Lky (in-plane): comprimento da própria barra.
    Lkx (out-of-plane): distância entre pontos travados lateralmente,
        percorrendo o grafo de adjacência do banzo. Transversais e
        contraventamentos provêm travamento lateral (NBR 8800 4.11/4.12).
    """
    # Nós travados: apoios + extremidades de transversais/contraventamentos.
    nos_travados = {nid for nid, n in nos.items() if n.support != "None"}
    for b in barras:
        if b.group in grupos_travamento:
            nos_travados.add(b.node_start)
            nos_travados.add(b.node_end)

    # Grafo de adjacência dos banzos.
    grafo_banzos: dict[str, list[tuple[str, float]]] = {}
    for b in barras:
        if b.group in grupos_banzo:
            grafo_banzos.setdefault(b.node_start, []).append((b.node_end, b.length))
            grafo_banzos.setdefault(b.node_end, []).append((b.node_start, b.length))

    lk_map: dict[int, tuple[float, float]] = {}
    for b in barras:
        lky = b.length  # in-plane
        if b.group not in grupos_banzo:
            lk_map[b.id] = (b.length, lky)
            continue

        # Varredura bidirecional para encontrar Lkx (out-of-plane).
        lkx = b.length
        for start, other in [(b.node_start, b.node_end), (b.node_end, b.node_start)]:
            curr, prev = start, other
            acumulado = 0.0
            while curr not in nos_travados:
                vizinhos = [(n, length) for n, length in grafo_banzos.get(curr, []) if n != prev]
                if not vizinhos:
                    break
                next_node, length = vizinhos[0]
                acumulado += length
                prev, curr = curr, next_node
            lkx = max(lkx, b.length + acumulado)

        lk_map[b.id] = (lkx, lky)

    return lk_map


def construir_e_resolver(
    nos_entrada: dict[str, NoFisico],
    barras_entrada: list[BarraFisica],
    perfil_por_grupo: dict[str, PerfilFisico],
    material: MaterialFisico,
    casos_carga_externos: list[dict],
    parametros_vento: ParametrosVento | None = None,
    nos_banzo_superior: list[str] | None = None,
    nos_fachada: list[str] | None = None,
    water_lamina_mm: float = 0.0,
    solo_tipo: str = "Rocha",
    custom_ks: float | None = None,
    footing_b: float = 0.6,
    footing_l: float = 0.6,
) -> ResultadoAnalise:
    """
    Constrói o modelo MEF, aplica cargas e resolve.

    Retorna um ResultadoAnalise com esforços, deslocamentos e peso.
    """
    resultado = ResultadoAnalise()
    resultado.nos = dict(nos_entrada)
    resultado.barras = [
        BarraFisica(
            id=b.id,
            node_start=b.node_start,
            node_end=b.node_end,
            group=b.group,
            length=b.length,
        )
        for b in barras_entrada
    ]

    if not barras_entrada:
        resultado.erro = "Nenhuma barra definida para análise."
        return resultado

    modelo = FEModel3D()

    # ----- Material (E em Pa, comprimentos em m, forças em N, rho em kg/m^3) -----
    modelo.add_material(
        material.nome,
        material.e_pa,
        material.g_pa,
        material.nu,
        material.rho_kg_m3,  # kg/m^3: consistente com E em Pa e lengths em m
        fy=material.fy_pa,
    )

    # ----- Seções (uma por perfil distinto) -----
    for perfil in perfil_por_grupo.values():
        if perfil.nome not in modelo.sections:
            modelo.add_section(
                perfil.nome,
                perfil.area_m2,
                perfil.iy_m4,  # PyNite: Iy = eixo forte
                perfil.ix_m4,  # PyNite: Iz = eixo fraco (convencionalmente chamado de Ix)
                perfil.j_m4,
            )

    # ----- Nós -----
    for nid, no in nos_entrada.items():
        modelo.add_node(nid, no.x, no.y, no.z)
        if no.support == "Pinned":
            modelo.def_support(nid, True, True, True, False, False, False)
        elif no.support == "Roller":
            # Roller restringe apenas Y (vertical) e Z (lateral).
            modelo.def_support(nid, False, True, True, False, False, False)
        elif no.support == "Fixed":
            modelo.def_support(nid, True, True, True, True, True, True)

    # ----- Barras -----
    # Mapa perfil por barra (importante para relatório).
    perfil_por_barra: dict[int, PerfilFisico] = {}
    for b in barras_entrada:
        perfil = perfil_por_grupo.get(b.group) or next(iter(perfil_por_grupo.values()))
        perfil_por_barra[b.id] = perfil
        try:
            modelo.add_member(
                f"M{b.id}",
                b.node_start,
                b.node_end,
                material.nome,
                perfil.nome,
            )
        except Exception as e:
            resultado.erro = f"Falha ao adicionar barra {b.id}: {e}"
            return resultado

    # ----- Cálculo do vão real -----
    xs_apoios = [no.x for no in nos_entrada.values() if no.support != "None"]
    vano_real = (
        (max(xs_apoios) - min(xs_apoios))
        if xs_apoios
        else max((abs(n.x) for n in nos_entrada.values()), default=0.0)
    )
    resultado.vano_real = max(vano_real, 0.1)

    # ----- Identificação do banzo superior -----
    if nos_banzo_superior is None:
        y_max = max((n.y for n in nos_entrada.values()), default=0.0)
        nos_banzo_superior = [nid for nid, n in nos_entrada.items() if abs(n.y - y_max) < 0.05]

    # ----- Casos de carga externos (G2 e Q) -----
    # PyNite exige um "case name" por caso de carga.
    casos_carga_ativos: set[str] = set()
    for i, caso in enumerate(casos_carga_externos):
        tipo = caso.get("type", "G")
        case_name = "Dead2" if tipo == "G" else ("Live" if tipo == "Q" else "Live")
        if case_name == "Live":
            case_name = f"Live_{i}" if "Live" in casos_carga_ativos else "Live"
        casos_carga_ativos.add(case_name)
        nos_alvo = caso.get("nodes") or nos_banzo_superior
        if not nos_alvo:
            continue
        valor_total = caso.get("value", 0.0)
        valor_por_no = valor_total / len(nos_alvo)
        for nid in nos_alvo:
            if nid in nos_entrada:
                modelo.add_node_load(
                    nid,
                    caso.get("direction", "FY"),
                    valor_por_no,
                    case=case_name,
                )

    # ----- Lâmina d'água (NBR 6120 item 5.6) -----
    if water_lamina_mm > 0 and nos_banzo_superior:
        # Peso = lamina(mm) * 10 N/m^2 por mm * área tributária.
        carga_agua = water_lamina_mm * 10.0  # N/m^2
        xs = [nos_entrada[nid].x for nid in nos_banzo_superior if nid in nos_entrada]
        zs = [nos_entrada[nid].z for nid in nos_banzo_superior if nid in nos_entrada]
        if xs and zs:
            area = (max(xs) - min(xs)) * (max(zs) - min(zs))
            carga_total = carga_agua * area
            carga_por_no = carga_total / len(nos_banzo_superior)
            for nid in nos_banzo_superior:
                if nid in nos_entrada:
                    modelo.add_node_load(nid, "FY", -carga_por_no, case="Water")

    # ----- Vento NBR 6123 -----
    if parametros_vento is not None:
        if nos_fachada is None:
            nos_fachada = identificar_fachadas_perpendiculares(
                nos_entrada, parametros_vento.direcao_graus
            )
        forcas = calcular_forcas_vento_3d(
            nos_entrada, parametros_vento, nos_banzo_superior, nos_fachada
        )
        for f in forcas:
            if f.no_id in nos_entrada:
                modelo.add_node_load(f.no_id, f.direction, f.valor, case="Wind")

    # ----- Carga de manutenção NBR 6120 (1 kN por nó do banzo superior) -----
    casos_manutencao: list[str] = []
    for i, nid in enumerate(nos_banzo_superior):
        if nid in nos_entrada:
            case_name = f"Maint_{i}"
            modelo.add_node_load(nid, "FY", -1000.0, case=case_name)
            casos_manutencao.append(case_name)

    # ----- Peso próprio (G1) -----
    # Distribuído igualmente nos nós das extremidades de cada barra.
    peso_total = 0.0
    pesos_nos: dict[str, float] = {nid: 0.0 for nid in nos_entrada}
    for b in barras_entrada:
        perfil = perfil_por_barra[b.id]
        unit_weight_kg_m = perfil.area_m2 * material.rho_kg_m3
        peso_barra_kg = unit_weight_kg_m * b.length
        peso_total += peso_barra_kg
        if b.node_start in pesos_nos:
            pesos_nos[b.node_start] += peso_barra_kg / 2
        if b.node_end in pesos_nos:
            pesos_nos[b.node_end] += peso_barra_kg / 2

    for nid, peso_kg in pesos_nos.items():
        if peso_kg > 0:
            modelo.add_node_load(nid, "FY", -peso_kg * 9.81, case="Dead1")

    resultado.peso_total_kg = peso_total

    # ----- Combinações ELU e ELS -----
    fatores_combo = {
        "ELU_Normal": {"Dead1": 1.25, "Dead2": 1.40, "Live": 1.50, "Wind": 1.40, "Water": 1.40},
        "ELU_Secundario": {"Dead1": 1.25, "Dead2": 1.40, "Live": 1.40, "Wind": 1.40, "Water": 1.40},
        "ELU_Alivio": {"Dead1": 1.00, "Dead2": 1.00, "Live": 1.50, "Wind": 0.00, "Water": 0.00},
        "ELU_Sem_Vento": {"Dead1": 1.25, "Dead2": 1.40, "Live": 1.50, "Wind": 0.00, "Water": 1.40},
        "ELU_Vento_Dominante": {
            "Dead1": 1.25,
            "Dead2": 1.40,
            "Live": 1.00,
            "Wind": 1.40,
            "Water": 1.40,
        },
        "ELS_Flecha_Total": {
            "Dead1": 1.00,
            "Dead2": 1.00,
            "Live": 1.00,
            "Wind": 0.00,
            "Water": 0.00,
        },
        "ELS_Permanente": {"Dead1": 1.00, "Dead2": 1.00, "Wind": 0.00, "Water": 0.00},
    }
    # Adiciona combinações de manutenção (uma por caso Maint_i).
    for i, _ in enumerate(casos_manutencao):
        nome = f"ELU_Maint_{i}"
        fatores_combo[nome] = {"Dead1": 1.25, "Dead2": 1.40, f"Maint_{i}": 1.50, "Live": 0.00}

    for nome, fatores in fatores_combo.items():
        with contextlib.suppress(Exception):
            modelo.add_load_combo(nome, fatores)

    # ----- Análise -----
    try:
        modelo.analyze(check_statics=False, check_stability=True)
    except Exception as e:
        resultado.erro = f"Falha na análise MEF: {e}"
        return resultado

    # ----- Extração de deslocamentos (flecha) -----
    max_flecha = 0.0
    max_contraflecha = 0.0
    for nid, no_modelo in modelo.nodes.items():
        dy_total = abs(no_modelo.DY.get("ELS_Flecha_Total", 0.0))
        dy_perm = abs(no_modelo.DY.get("ELS_Permanente", 0.0))
        if dy_total > max_flecha:
            max_flecha = dy_total
        if dy_perm > max_contraflecha:
            max_contraflecha = dy_perm
        # Deslocamentos para visualização.
        dx = no_modelo.DX.get("ELS_Flecha_Total", 0.0)
        dz = no_modelo.DZ.get("ELS_Flecha_Total", 0.0)
        resultado.deslocamentos[nid] = (dx, dy_total, dz)

    # Limite de divergência numérica.
    if max_flecha > 2.0:
        resultado.erro = "Deslocamento excessivo: possível instabilidade."
        return resultado

    resultado.flecha_maxima = max_flecha
    resultado.contraflecha = max_contraflecha

    # ----- Cálculo do Lk por barra -----
    lk_map = calcular_lk_banzos(resultado.barras, resultado.nos)

    # ----- Envoltória de esforços por barra -----
    combos_elu_nomes = [
        n for n in fatores_combo if n.startswith("ELU_") and not n.startswith("ELS_")
    ]
    utilizacao_maxima = 0.0

    for b in resultado.barras:
        mid_str = f"M{b.id}"
        if mid_str not in modelo.members:
            continue
        membro = modelo.members[mid_str]

        # Envoltória axial.
        axiais = []
        for c in combos_elu_nomes:
            try:
                axiais.append(membro.max_axial(c))
                axiais.append(membro.min_axial(c))
            except Exception:
                pass
        axiais = [
            a for a in axiais if not (isinstance(a, float) and (math.isnan(a) or math.isinf(a)))
        ]
        if not axiais:
            resultado.erro = f"Sem esforços na barra {b.id}."
            continue
        axial = max(axiais, key=abs)

        # Envoltória momento Y.
        mys = []
        for c in combos_elu_nomes:
            try:
                mys.append(membro.max_moment("my", c))
                mys.append(membro.min_moment("my", c))
            except Exception:
                pass
        mys = [m for m in mys if not (isinstance(m, float) and (math.isnan(m) or math.isinf(m)))]
        my = max(mys, key=abs) if mys else 0.0

        # Envoltória momento Z.
        mzs = []
        for c in combos_elu_nomes:
            try:
                mzs.append(membro.max_moment("mz", c))
                mzs.append(membro.min_moment("mz", c))
            except Exception:
                pass
        mzs = [m for m in mzs if not (isinstance(m, float) and (math.isnan(m) or math.isinf(m)))]
        mz = max(mzs, key=abs) if mzs else 0.0

        b.axial_force = float(axial)
        b.my = float(my)
        b.mz = float(mz)
        b.stress_type = "Tração" if axial > 0 else "Compressão"

        # Verificação NBR 8800.
        perfil = perfil_por_barra[b.id]
        lkx, lky = lk_map.get(b.id, (b.length, b.length))
        b.lkx = lkx
        b.lky = lky
        verif = verificar_barra_nbr8800(b, perfil, material, lkx=lkx, lky=lky)
        b.utilization = verif.utilization
        b.n_rd = verif.n_rd
        b.m_rd = verif.m_rd
        b.esbeltez = verif.esbeltez
        b.fator_chi = verif.fator_chi
        b.fator_q = verif.fator_q
        b.profile_name = perfil.nome

        utilizacao_maxima = max(utilizacao_maxima, verif.utilization)

    resultado.utilizacao_maxima = utilizacao_maxima
    return resultado
