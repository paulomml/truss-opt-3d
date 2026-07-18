"""
Solver MEF baseado em PyNite v3.
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
# Valores em kN/m^3 (Padrao Terzaghi para placa 0.30x0.30 m).
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


class ModeloBaseFEA:
    """
    Modelo MEF reutilizável para acelerar avaliações do GA.

    Constrói o modelo PyNite uma única vez com geometria, material,
    cargas invariantes (Dead2, Live, vento, água, manutenção) e combinações.
    O método resolver(perfil_por_grupo) atualiza as seções das barras,
    recalcula peso próprio (Dead1) e re-analisa, sem recriar o modelo.
    """

    def __init__(
        self,
        nos: dict[str, NoFisico],
        barras: list[BarraFisica],
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
        perfis_disponiveis: list[PerfilFisico] | None = None,
    ):
        self.nos = nos
        self.barras = barras
        self.material = material
        self.perfis_disponiveis = perfis_disponiveis or []

        # Vão real (invariante)
        xs_apoios = [no.x for no in nos.values() if no.support != "None"]
        self.vano_real = max(
            (max(xs_apoios) - min(xs_apoios)) if xs_apoios else 0.0,
            0.1,
        )
        if not xs_apoios:
            self.vano_real = max((abs(n.x) for n in nos.values()), default=0.1)

        # Banzo superior
        if nos_banzo_superior is None:
            y_max = max((n.y for n in nos.values()), default=0.0)
            self.nos_banzo_superior = [nid for nid, n in nos.items() if abs(n.y - y_max) < 0.05]
        else:
            self.nos_banzo_superior = nos_banzo_superior
        self.nos_fachada = nos_fachada

        # Pré-calcular Lk (invariante: só depende da geometria)
        self.lk_map = calcular_lk_banzos(barras, nos)

        self._primeira_chamada = True

        # Construir modelo PyNite.
        self.modelo = FEModel3D()

        # 1) Material
        self.modelo.add_material(
            material.nome,
            material.e_pa,
            material.g_pa,
            material.nu,
            material.rho_kg_m3,
            fy=material.fy_pa,
        )

        # 2) Seções (todos os perfis disponíveis, adicionados uma vez)
        for perfil in self.perfis_disponiveis:
            if perfil.nome not in self.modelo.sections:
                self.modelo.add_section(
                    perfil.nome,
                    perfil.area_m2,
                    perfil.iy_m4,
                    perfil.ix_m4,
                    perfil.j_m4,
                )

        # 3) Nós e apoios
        usar_ise = solo_tipo is not None and solo_tipo != "Rocha"
        for nid, no in nos.items():
            self.modelo.add_node(nid, no.x, no.y, no.z)
            if no.support == "Pinned":
                if usar_ise:
                    self.modelo.def_support(nid, True, False, True, False, False, False)
                else:
                    self.modelo.def_support(nid, True, True, True, False, False, False)
            elif no.support == "Roller":
                if usar_ise:
                    self.modelo.def_support(nid, False, False, True, False, False, False)
                else:
                    self.modelo.def_support(nid, False, True, True, False, False, False)
            elif no.support == "Fixed":
                self.modelo.def_support(nid, True, True, True, True, True, True)

        # 4) ISE: molas Winkler
        self.dados_ise: dict = {}
        if usar_ise:
            solo_info = BANCO_SOLOS.get(solo_tipo, BANCO_SOLOS["Rocha"])
            ks1_kN_m3 = (
                custom_ks
                if (solo_tipo == "Customizado" and custom_ks is not None)
                else solo_info["ks1"]
            )
            B = max(footing_b, 0.305)
            if solo_info["tipo"] == "granular":
                ks_kN_m3 = ks1_kN_m3 * ((B + 0.305) / (2 * B)) ** 2
            elif solo_info["tipo"] == "coesivo":
                ks_kN_m3 = ks1_kN_m3 * (0.305 / B)
            else:
                ks_kN_m3 = ks1_kN_m3
            ks = ks_kN_m3 * 1000.0
            K_y = ks * B * footing_l
            I_x = footing_l * B**3 / 12
            I_z = B * footing_l**3 / 12
            K_theta_x = ks * I_x
            K_theta_z = ks * I_z
            self.dados_ise = {
                "solo_tipo": solo_tipo,
                "ks1_kN_m3": ks1_kN_m3,
                "ks_kN_m3": ks_kN_m3,
                "K_y_N_m": K_y,
                "K_theta_x_Nm_rad": K_theta_x,
                "K_theta_z_Nm_rad": K_theta_z,
                "footing_b_m": footing_b,
                "footing_l_m": footing_l,
                "I_x_m4": I_x,
                "I_z_m4": I_z,
                "usar_ise": True,
            }
            for nid, no in nos.items():
                if no.support in ("Pinned", "Roller"):
                    self.modelo.def_support_spring(nid, "DY", K_y)
                    self.modelo.def_support_spring(nid, "RX", K_theta_x)
                    self.modelo.def_support_spring(nid, "RZ", K_theta_z)

        # 5) Barras (com seção padrão temporária)
        secao_padrao = (
            self.perfis_disponiveis[0].nome
            if self.perfis_disponiveis
            else next(iter(self.modelo.sections), None)
        )
        for b in barras:
            self.modelo.add_member(
                f"M{b.id}", b.node_start, b.node_end, material.nome, secao_padrao
            )

        # 6) Cargas externas (Dead2 / Live)
        casos_carga_ativos: set[str] = set()
        for i, caso in enumerate(casos_carga_externos):
            tipo = caso.get("type", "G")
            case_name = "Dead2" if tipo == "G" else ("Live" if tipo == "Q" else "Live")
            if case_name == "Live":
                case_name = f"Live_{i}" if "Live" in casos_carga_ativos else "Live"
            casos_carga_ativos.add(case_name)
            nos_alvo = caso.get("nodes") or self.nos_banzo_superior
            if not nos_alvo:
                continue
            valor_total = caso.get("value", 0.0)
            valor_por_no = valor_total / len(nos_alvo)
            for nid in nos_alvo:
                if nid in nos:
                    self.modelo.add_node_load(
                        nid, caso.get("direction", "FY"), valor_por_no, case=case_name
                    )

        # 7) Lâmina d'água
        if water_lamina_mm > 0 and self.nos_banzo_superior:
            carga_agua = water_lamina_mm * 10.0
            xs = [nos[nid].x for nid in self.nos_banzo_superior if nid in nos]
            zs = [nos[nid].z for nid in self.nos_banzo_superior if nid in nos]
            if xs and zs:
                area = (max(xs) - min(xs)) * (max(zs) - min(zs))
                carga_total = carga_agua * area
                carga_por_no = carga_total / len(self.nos_banzo_superior)
                for nid in self.nos_banzo_superior:
                    if nid in nos:
                        self.modelo.add_node_load(nid, "FY", -carga_por_no, case="Water")

        # 8) Vento NBR 6123
        if parametros_vento is not None:
            fachadas = nos_fachada
            if fachadas is None:
                fachadas = identificar_fachadas_perpendiculares(nos, parametros_vento.direcao_vento_graus)
            forcas = calcular_forcas_vento_3d(
                nos, parametros_vento, self.nos_banzo_superior, fachadas
            )
            for f in forcas:
                if f.no_id in nos:
                    self.modelo.add_node_load(f.no_id, f.direction, f.valor, case="Wind")
            # Guarda metadados do vento para o memorial.
            area_frontal = (
                (max(n.x for n in nos.values()) - min(n.x for n in nos.values()))
                * (max(n.y for n in nos.values()) - min(n.y for n in nos.values()))
                if nos else 0.0
            )
            ca_arrasto = getattr(parametros_vento, 'ca_arrasto', 1.3)
            q = 0.613 * (parametros_vento.v0_mps * parametros_vento.s1 * parametros_vento.s2 * parametros_vento.s3) ** 2
            forca_arrasto_total = ca_arrasto * q * area_frontal if area_frontal > 0 else abs(sum(f.valor for f in forcas))
            self.dados_vento = {
                "v0_mps": parametros_vento.v0_mps,
                "s1": parametros_vento.s1,
                "s2": parametros_vento.s2,
                "s3": parametros_vento.s3,
                "direcao_graus": parametros_vento.direcao_vento_graus,
                "ce_externo": parametros_vento.ce_externo,
                "ci_interno": parametros_vento.ci_interno,
                "ca_arrasto": ca_arrasto,
                "area_frontal_m2": area_frontal,
                "forca_arrasto_total_N": forca_arrasto_total,
                "num_forcas_nodais": len(forcas),
            }
        else:
            self.dados_vento = {}

        # 9) Manutenção (1 kN por nó do banzo superior)
        self.casos_manutencao: list[str] = []
        for i, nid in enumerate(self.nos_banzo_superior):
            if nid in nos:
                case_name = f"Maint_{i}"
                self.modelo.add_node_load(nid, "FY", -1000.0, case=case_name)
                self.casos_manutencao.append(case_name)

        # NOTA: Dead1 (peso próprio) é aplicado em resolver()

        # 10) Combinações ELU e ELS
        # Combos core (sempre necessários para o GA).
        self.fatores_core = {
            "ELU_Normal": {"Dead1": 1.25, "Dead2": 1.40, "Live": 1.50, "Wind": 1.40, "Water": 1.40},
            "ELU_Secundario": {
                "Dead1": 1.25,
                "Dead2": 1.40,
                "Live": 1.40,
                "Wind": 1.40,
                "Water": 1.40,
            },
            "ELU_Alivio": {"Dead1": 1.00, "Dead2": 1.00, "Live": 1.50, "Wind": 0.00, "Water": 0.00},
            "ELU_Sem_Vento": {
                "Dead1": 1.25,
                "Dead2": 1.40,
                "Live": 1.50,
                "Wind": 0.00,
                "Water": 1.40,
            },
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
            "ELS_Flecha_Frequente": {
                "Dead1": 1.00,
                "Dead2": 1.00,
                "Live": 0.5,
                "Wind": 0.00,
                "Water": 0.00,
            },
            "ELS_Flecha_Permanente": {
                "Dead1": 1.00,
                "Dead2": 1.00,
                "Live": 0.3,
                "Wind": 0.00,
                "Water": 0.00,
            },
            "ELS_Permanente": {"Dead1": 1.00, "Dead2": 1.00, "Wind": 0.00, "Water": 0.00},
        }
        # Combos de manutenção (separados, adicionados sob demanda).
        self.fatores_manutencao: dict[str, dict[str, float]] = {}
        for i, _ in enumerate(self.casos_manutencao):
            nome = f"ELU_Maint_{i}"
            self.fatores_manutencao[nome] = {
                "Dead1": 1.25,
                "Dead2": 1.40,
                f"Maint_{i}": 1.50,
                "Live": 0.00,
            }

        # Adicionar apenas combos core ao modelo.
        for nome, fatores in self.fatores_core.items():
            with contextlib.suppress(Exception):
                self.modelo.add_load_combo(nome, fatores)

    def resolver(
        self,
        perfil_por_grupo: dict[str, PerfilFisico],
        incluir_manutencao: bool = False,
    ) -> ResultadoAnalise:
        """
        Executa análise com os perfis especificados, reusando o modelo base.

        Args:
            perfil_por_grupo: mapeamento grupo -> PerfilFisico
            incluir_manutencao: se True, adiciona combos de manutenção
                temporariamente antes de analisar.

        Returns:
            ResultadoAnalise com esforços, deslocamentos e verificação NBR 8800.
        """
        resultado = ResultadoAnalise()
        resultado.nos = dict(self.nos)
        resultado.barras = [
            BarraFisica(
                id=b.id,
                node_start=b.node_start,
                node_end=b.node_end,
                group=b.group,
                length=b.length,
            )
            for b in self.barras
        ]
        resultado.vano_real = self.vano_real

        # Mapa perfil por barra
        perfil_por_barra: dict[int, PerfilFisico] = {}
        for b in self.barras:
            perfil = perfil_por_grupo.get(b.group) or next(iter(perfil_por_grupo.values()))
            perfil_por_barra[b.id] = perfil

        # Atualizar seções das barras no modelo PyNite
        for b in self.barras:
            mid = f"M{b.id}"
            if mid not in self.modelo.members:
                continue
            self.modelo.members[mid].section_name = perfil_por_barra[b.id].nome

        # Remover cargas Dead1 anteriores e recalcular peso próprio.
        # PyNite v3 armazena cargas nodais em NodeLoads: list[(direction, P, case)].
        for node in self.modelo.nodes.values():
            node.NodeLoads = [ld for ld in node.NodeLoads if ld[2] != "Dead1"]

        peso_total = 0.0
        pesos_nos: dict[str, float] = {nid: 0.0 for nid in self.nos}
        for b in self.barras:
            perfil = perfil_por_barra[b.id]
            unit_weight_kg_m = perfil.area_m2 * self.material.rho_kg_m3
            peso_barra_kg = unit_weight_kg_m * b.length
            peso_total += peso_barra_kg
            pesos_nos[b.node_start] += peso_barra_kg / 2
            pesos_nos[b.node_end] += peso_barra_kg / 2

        for nid, peso_kg in pesos_nos.items():
            if peso_kg > 0 and nid in self.modelo.nodes:
                self.modelo.nodes[nid].NodeLoads.append(("FY", -peso_kg * 9.81, "Dead1"))

        resultado.peso_total_kg = peso_total

        # Adicionar combos de manutenção sob demanda (modo_rapido=False).
        if incluir_manutencao:
            for nome, fatores in self.fatores_manutencao.items():
                with contextlib.suppress(Exception):
                    self.modelo.add_load_combo(nome, fatores)

        # analyze_linear() monta K uma única vez (vs analyze() que monta por
        # combo). Equivalente quando não há T/C-only ou P-Delta.
        try:
            self.modelo.analyze_linear(
                check_statics=False,
                check_stability=self._primeira_chamada,
            )
            self._primeira_chamada = False
        except Exception as e:
            resultado.erro = f"Falha na análise MEF: {e}"
            return resultado

        # Remover combos de manutenção após análise.
        if incluir_manutencao:
            for nome in self.fatores_manutencao:
                self.modelo.load_combos.pop(nome, None)

        # Extração de deslocamentos
        max_flecha = 0.0
        max_contraflecha = 0.0
        for nid, no_modelo in self.modelo.nodes.items():
            dy_total = abs(no_modelo.DY.get("ELS_Flecha_Total", 0.0))
            dy_perm = abs(no_modelo.DY.get("ELS_Permanente", 0.0))
            if dy_total > max_flecha:
                max_flecha = dy_total
            if dy_perm > max_contraflecha:
                max_contraflecha = dy_perm
            dx = no_modelo.DX.get("ELS_Flecha_Total", 0.0)
            dz = no_modelo.DZ.get("ELS_Flecha_Total", 0.0)
            resultado.deslocamentos[nid] = (dx, dy_total, dz)

        if max_flecha > 2.0:
            resultado.erro = "Deslocamento excessivo: possível instabilidade."
            return resultado

        resultado.flecha_maxima = max_flecha
        resultado.contraflecha = max_contraflecha

        # Envoltória de esforços por barra
        fatores_ativos = (
            {**self.fatores_core, **self.fatores_manutencao}
            if incluir_manutencao
            else self.fatores_core
        )
        combos_elu_nomes = [
            n for n in fatores_ativos if n.startswith("ELU_") and not n.startswith("ELS_")
        ]
        utilizacao_maxima = 0.0

        for b in resultado.barras:
            mid_str = f"M{b.id}"
            if mid_str not in self.modelo.members:
                continue
            membro = self.modelo.members[mid_str]

            # Otimização: extrair axial, my e mz PARA A MESMA COMBO em cada
            # iteração. Cada chamada max_axial(c)/max_moment(dir, c) re-segmenta
            # o membro quando a combo muda (via _segment_member). Ao agrupar
            # todas as direções por combo, evitamos re-segmentação entre
            # direções e reduzimos as chamadas de N_combos * 3 direções para
            # apenas N_combos segmentações por barra.
            axiais: list[float] = []
            mys: list[float] = []
            mzs: list[float] = []
            for c in combos_elu_nomes:
                try:
                    axiais.append(membro.max_axial(c))
                    axiais.append(membro.min_axial(c))
                    mys.append(membro.max_moment("my", c))
                    mys.append(membro.min_moment("my", c))
                    mzs.append(membro.max_moment("mz", c))
                    mzs.append(membro.min_moment("mz", c))
                except Exception:
                    pass
            axiais = [
                a for a in axiais if not (isinstance(a, float) and (math.isnan(a) or math.isinf(a)))
            ]
            if not axiais:
                resultado.erro = f"Sem esforços na barra {b.id}."
                continue
            axial = max(axiais, key=abs)

            mys = [
                m for m in mys if not (isinstance(m, float) and (math.isnan(m) or math.isinf(m)))
            ]
            my = max(mys, key=abs) if mys else 0.0

            mzs = [
                m for m in mzs if not (isinstance(m, float) and (math.isnan(m) or math.isinf(m)))
            ]
            mz = max(mzs, key=abs) if mzs else 0.0

            b.axial_force = float(axial)
            b.my = float(my)
            b.mz = float(mz)
            b.stress_type = "Tração" if axial > 0 else "Compressão"

            # Verificação NBR 8800
            perfil = perfil_por_barra[b.id]
            lkx, lky = self.lk_map.get(b.id, (b.length, b.length))
            b.lkx = lkx
            b.lky = lky
            verif = verificar_barra_nbr8800(b, perfil, self.material, lkx=lkx, lky=lky)
            b.utilization = verif.utilization
            b.n_rd = verif.n_rd
            b.m_rd = verif.m_rd
            b.esbeltez = verif.esbeltez
            b.fator_chi = verif.fator_chi
            b.fator_q = verif.fator_q
            b.lambda_0 = verif.lambda_0
            b.detalhes = verif.detalhes
            b.violacao_normativa = verif.violacao_normativa
            b.peso_kg = perfil.area_m2 * self.material.rho_kg_m3 * b.length
            b.profile_name = perfil.nome

            utilizacao_maxima = max(utilizacao_maxima, verif.utilization)

        resultado.utilizacao_maxima = utilizacao_maxima

        # Dados extras para o memorial (ISE, vento, peso por grupo).
        resultado.dados_extras["ise"] = self.dados_ise
        resultado.dados_extras["vento"] = self.dados_vento
        # Peso por grupo
        peso_por_grupo: dict[str, float] = {}
        for b in resultado.barras:
            grupo = b.group or "Padrão"
            peso_por_grupo[grupo] = peso_por_grupo.get(grupo, 0.0) + b.peso_kg
        resultado.dados_extras["peso_por_grupo"] = peso_por_grupo
        # Distribuição de utilização
        usos = [b.utilization for b in resultado.barras]
        resultado.dados_extras["stats_utilizacao"] = {
            "min": min(usos) if usos else 0.0,
            "max": max(usos) if usos else 0.0,
            "avg": sum(usos) / len(usos) if usos else 0.0,
            "acima_80": sum(1 for u in usos if u > 0.8),
            "violadas": sum(1 for u in usos if u > 1.0),
        }
        # Barra mais solicitada e nó com maior flecha
        if resultado.barras:
            pior = max(resultado.barras, key=lambda x: x.utilization)
            resultado.dados_extras["barra_critica"] = {
                "id": pior.id, "grupo": pior.group, "utilization": pior.utilization
            }
        if resultado.deslocamentos:
            no_max_flecha = max(
                resultado.deslocamentos, key=lambda nid: abs(resultado.deslocamentos[nid][1])
            )
            resultado.dados_extras["no_max_flecha"] = {
                "id": no_max_flecha,
                "dy_mm": abs(resultado.deslocamentos[no_max_flecha][1]) * 1000,
            }
        return resultado


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

    # Material (E em Pa, comprimentos em m, forças em N, rho em kg/m3)
    modelo.add_material(
        material.nome,
        material.e_pa,
        material.g_pa,
        material.nu,
        material.rho_kg_m3,  # kg/m^3: consistente com E em Pa e lengths em m
        fy=material.fy_pa,
    )

    # Seções (uma por perfil distinto)
    for perfil in perfil_por_grupo.values():
        if perfil.nome not in modelo.sections:
            modelo.add_section(
                perfil.nome,
                perfil.area_m2,
                perfil.iy_m4,  # PyNite: Iy = eixo forte
                perfil.ix_m4,  # PyNite: Iz = eixo fraco (convencionalmente chamado de Ix)
                perfil.j_m4,
            )

    # Nós
    for nid, no in nos_entrada.items():
        modelo.add_node(nid, no.x, no.y, no.z)

        usar_ise = solo_tipo is not None and solo_tipo != "Rocha"

        if no.support == "Pinned":
            if usar_ise:
                modelo.def_support(nid, True, False, True, False, False, False)
            else:
                modelo.def_support(nid, True, True, True, False, False, False)
        elif no.support == "Roller":
            if usar_ise:
                modelo.def_support(nid, False, False, True, False, False, False)
            else:
                modelo.def_support(nid, False, True, True, False, False, False)
        elif no.support == "Fixed":
            modelo.def_support(nid, True, True, True, True, True, True)

    # ISE: aplicar molas Winkler nos nós de base
    if solo_tipo is not None and solo_tipo != "Rocha":
        solo_info = BANCO_SOLOS.get(solo_tipo, BANCO_SOLOS["Rocha"])
        ks1_kN_m3 = (
            custom_ks
            if (solo_tipo == "Customizado" and custom_ks is not None)
            else solo_info["ks1"]
        )
        B = max(footing_b, 0.305)
        if solo_info["tipo"] == "granular":
            ks_kN_m3 = ks1_kN_m3 * ((B + 0.305) / (2 * B)) ** 2
        elif solo_info["tipo"] == "coesivo":
            ks_kN_m3 = ks1_kN_m3 * (0.305 / B)
        else:
            ks_kN_m3 = ks1_kN_m3

        ks = ks_kN_m3 * 1000.0  # kN/m^3 para N/m^3

        K_y = ks * B * footing_l  # N/m
        I_x = footing_l * B**3 / 12  # m4
        I_z = B * footing_l**3 / 12  # m4
        K_theta_x = ks * I_x  # Nm/rad
        K_theta_z = ks * I_z  # Nm/rad

        for nid, no in nos_entrada.items():
            if no.support in ("Pinned", "Roller"):
                modelo.def_support_spring(nid, "DY", K_y)
                modelo.def_support_spring(nid, "RX", K_theta_x)
                modelo.def_support_spring(nid, "RZ", K_theta_z)

    # Barras
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

    # Cálculo do vão real
    xs_apoios = [no.x for no in nos_entrada.values() if no.support != "None"]
    vano_real = (
        (max(xs_apoios) - min(xs_apoios))
        if xs_apoios
        else max((abs(n.x) for n in nos_entrada.values()), default=0.0)
    )
    resultado.vano_real = max(vano_real, 0.1)

    # Identificação do banzo superior
    if nos_banzo_superior is None:
        y_max = max((n.y for n in nos_entrada.values()), default=0.0)
        nos_banzo_superior = [nid for nid, n in nos_entrada.items() if abs(n.y - y_max) < 0.05]

    # Casos de carga externos (G2 e Q)
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

    # Lamina d'agua (NBR 6120 item 5.6)
    if water_lamina_mm > 0 and nos_banzo_superior:
        # Peso = lâmina(mm) * 10 N/m^2 por mm * área tributária.
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

    # Vento NBR 6123
    if parametros_vento is not None:
        if nos_fachada is None:
            nos_fachada = identificar_fachadas_perpendiculares(
                nos_entrada, parametros_vento.direcao_vento_graus
            )
        forcas = calcular_forcas_vento_3d(
            nos_entrada, parametros_vento, nos_banzo_superior, nos_fachada
        )
        for f in forcas:
            if f.no_id in nos_entrada:
                modelo.add_node_load(f.no_id, f.direction, f.valor, case="Wind")

    # Carga de manutenção NBR 6120 (1 kN por nó do banzo superior)
    casos_manutencao: list[str] = []
    for i, nid in enumerate(nos_banzo_superior):
        if nid in nos_entrada:
            case_name = f"Maint_{i}"
            modelo.add_node_load(nid, "FY", -1000.0, case=case_name)
            casos_manutencao.append(case_name)

    # Peso próprio (G1)
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

    # Combinações ELU e ELS
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
        "ELS_Flecha_Frequente": {
            "Dead1": 1.00,
            "Dead2": 1.00,
            "Live": 0.5,
            "Wind": 0.00,
            "Water": 0.00,
        },
        "ELS_Flecha_Permanente": {
            "Dead1": 1.00,
            "Dead2": 1.00,
            "Live": 0.3,
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

    # Análise.
    # Otimização: usar analyze_linear() (monta K uma única vez em vez de uma
    # vez por combinação de carga). Válido porque este modelo não usa elementos
    # tension-only/compression-only nem análise P-Delta. Resultados idênticos.
    try:
        modelo.analyze_linear(check_statics=False, check_stability=True)
    except Exception as e:
        resultado.erro = f"Falha na análise MEF: {e}"
        return resultado

    # Extração de deslocamentos (flecha)
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

    # Cálculo do Lk por barra
    lk_map = calcular_lk_banzos(resultado.barras, resultado.nos)

    # Envoltória de esforços por barra
    combos_elu_nomes = [
        n for n in fatores_combo if n.startswith("ELU_") and not n.startswith("ELS_")
    ]
    utilizacao_maxima = 0.0

    for b in resultado.barras:
        mid_str = f"M{b.id}"
        if mid_str not in modelo.members:
            continue
        membro = modelo.members[mid_str]

        # Otimização: extrair axial, my e mz PARA A MESMA COMBO em cada
        # iteração. Reduz re-segmentação do membro entre direções.
        axiais = []
        mys = []
        mzs = []
        for c in combos_elu_nomes:
            try:
                axiais.append(membro.max_axial(c))
                axiais.append(membro.min_axial(c))
                mys.append(membro.max_moment("my", c))
                mys.append(membro.min_moment("my", c))
                mzs.append(membro.max_moment("mz", c))
                mzs.append(membro.min_moment("mz", c))
            except Exception:
                pass
        axiais = [
            a for a in axiais if not (isinstance(a, float) and (math.isnan(a) or math.isinf(a)))
        ]
        if not axiais:
            resultado.erro = f"Sem esforços na barra {b.id}."
            continue
        axial = max(axiais, key=abs)

        mys = [m for m in mys if not (isinstance(m, float) and (math.isnan(m) or math.isinf(m)))]
        my = max(mys, key=abs) if mys else 0.0

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
        b.lambda_0 = verif.lambda_0
        b.detalhes = verif.detalhes
        b.violacao_normativa = verif.violacao_normativa
        b.peso_kg = perfil.area_m2 * material.rho_kg_m3 * b.length
        b.profile_name = perfil.nome

        utilizacao_maxima = max(utilizacao_maxima, verif.utilization)

    resultado.utilizacao_maxima = utilizacao_maxima

    # Dados extras para o memorial (ISE, vento, peso por grupo)
    solo_tipo_local = solo_tipo or "Rocha"
    if solo_tipo_local != "Rocha":
        solo_info_local = {
            "Areia Fofa": {"ks1": 15000, "tipo": "granular"},
            "Areia Compacta": {"ks1": 100000, "tipo": "granular"},
            "Argila Mole": {"ks1": 10000, "tipo": "coesivo"},
            "Argila Rija": {"ks1": 40000, "tipo": "coesivo"},
            "Rocha": {"ks1": 250000, "tipo": "rigido"},
            "Customizado": {"ks1": 50000, "tipo": "coesivo"},
        }.get(solo_tipo_local, {"ks1": 50000, "tipo": "coesivo"})
        ks1_local = custom_ks if (solo_tipo_local == "Customizado" and custom_ks is not None) else solo_info_local["ks1"]
        B_local = max(footing_b, 0.305)
        if solo_info_local["tipo"] == "granular":
            ks_local = ks1_local * ((B_local + 0.305) / (2 * B_local)) ** 2
        elif solo_info_local["tipo"] == "coesivo":
            ks_local = ks1_local * (0.305 / B_local)
        else:
            ks_local = ks1_local
        K_y_local = ks_local * 1000.0 * B_local * footing_l
        I_x_local = footing_l * B_local**3 / 12
        I_z_local = B_local * footing_l**3 / 12
        resultado.dados_extras["ise"] = {
            "solo_tipo": solo_tipo_local,
            "ks1_kN_m3": ks1_local,
            "ks_kN_m3": ks_local,
            "K_y_N_m": K_y_local,
            "K_theta_x_Nm_rad": ks_local * 1000.0 * I_x_local,
            "K_theta_z_Nm_rad": ks_local * 1000.0 * I_z_local,
            "footing_b_m": footing_b,
            "footing_l_m": footing_l,
            "I_x_m4": I_x_local,
            "I_z_m4": I_z_local,
            "usar_ise": True,
        }
    else:
        resultado.dados_extras["ise"] = {"solo_tipo": solo_tipo_local, "usar_ise": False}
    # Vento
    if parametros_vento is not None:
        area_frontal = (
            (max(n.x for n in nos_entrada.values()) - min(n.x for n in nos_entrada.values()))
            * (max(n.y for n in nos_entrada.values()) - min(n.y for n in nos_entrada.values()))
            if nos_entrada else 0.0
        )
        ca_arrasto = getattr(parametros_vento, 'ca_arrasto', 1.3)
        q_local = 0.613 * (parametros_vento.v0_mps * parametros_vento.s1 * parametros_vento.s2 * parametros_vento.s3) ** 2
        resultado.dados_extras["vento"] = {
            "v0_mps": parametros_vento.v0_mps,
            "s1": parametros_vento.s1,
            "s2": parametros_vento.s2,
            "s3": parametros_vento.s3,
            "direcao_graus": parametros_vento.direcao_vento_graus,
            "ce_externo": parametros_vento.ce_externo,
            "ci_interno": parametros_vento.ci_interno,
            "ca_arrasto": ca_arrasto,
            "area_frontal_m2": area_frontal,
        }
    else:
        resultado.dados_extras["vento"] = {}
    # Peso por grupo
    peso_por_grupo: dict[str, float] = {}
    for b in resultado.barras:
        grp = b.group or "Padrão"
        peso_por_grupo[grp] = peso_por_grupo.get(grp, 0.0) + b.peso_kg
    resultado.dados_extras["peso_por_grupo"] = peso_por_grupo
    # Distribuição de utilização
    usos = [b.utilization for b in resultado.barras]
    resultado.dados_extras["stats_utilizacao"] = {
        "min": min(usos) if usos else 0.0,
        "max": max(usos) if usos else 0.0,
        "avg": sum(usos) / len(usos) if usos else 0.0,
        "acima_80": sum(1 for u in usos if u > 0.8),
        "violadas": sum(1 for u in usos if u > 1.0),
    }
    if resultado.barras:
        pior = max(resultado.barras, key=lambda x: x.utilization)
        resultado.dados_extras["barra_critica"] = {
            "id": pior.id, "grupo": pior.group, "utilization": pior.utilization
        }
    if resultado.deslocamentos:
        no_max = max(resultado.deslocamentos, key=lambda nid: abs(resultado.deslocamentos[nid][1]))
        resultado.dados_extras["no_max_flecha"] = {
            "id": no_max, "dy_mm": abs(resultado.deslocamentos[no_max][1]) * 1000
        }
    return resultado
