import numpy as np
from Pynite import FEModel3D
from domain.models import TrussRequest, NodeResult, MemberResult
import math

# Coeficiente de reação do subleito (ks1) via Winkler-Terzaghi.
# Referência: Ensaio de placa normatizado (30,5 cm). Usado como rigidez de mola base.
SOIL_DATABASE = {
    "Areia Fofa": {"ks1": 15000, "type": "granular"},
    "Areia Compacta": {"ks1": 100000, "type": "granular"},
    "Argila Mole": {"ks1": 10000, "type": "coesivo"},
    "Argila Rija": {"ks1": 40000, "type": "coesivo"},
    "Rocha": {"ks1": 250000, "type": "rigid"},
}


import re


def calculate_max_utilization(
    force, mz, my, profile, length, material, group_name="Padrão", lkx=None, lky=None
):
    """
    Determina a Taxa de Utilização (U) conforme NBR 8800:2008.
    
    Verifica:
    1. Esbeltez Global (Lambda <= 200/300) - Item 5.3.4.1.
    2. Flambagem Local (Fator Q) - Tabela F.1.
    3. Capacidade Axial (N_rd) - Euler + Chi.
    4. Capacidade Flexural (M_rd) - Regime Elástico.
    5. Interação Esforços Combinados (N + M) - Item 5.5.
    """
    gamma_a1 = 1.10
    fy = (material["fy"] * 1e6) / gamma_a1
    E = material["E"] * 1e9
    A = profile["Area_m2"]

    # Inércias e raios de giração para ambos os eixos principais.
    rx = math.sqrt(profile["Ix_m4"] / A)
    ry = math.sqrt(profile["Iy_m4"] / A)

    # Comprimento de flambagem (Lk): Default é o comprimento real da barra.
    lkx = lkx if lkx is not None else length
    lky = lky if lky is not None else length
    slenderness_x = lkx / rx
    slenderness_y = lky / ry
    slenderness_max = max(slenderness_x, slenderness_y)

    # Verificação de limites de esbeltez normativa (NBR 8800).
    # Compressão: Limite mandatório lambda <= 200 (Item 5.3.4.1).
    if force < -0.01 and slenderness_max > 200:
        return 999.0
    # Tração: Recomendação lambda <= 300 (Item 5.2.8.1).
    if force >= -0.01 and slenderness_max > 300:
        return 999.0

    # -------------------------------------------------------------------------
    # FLAMBAGEM LOCAL (FATOR Q) - Tabela F.1
    # -------------------------------------------------------------------------
    # Extração de dimensões nominais da seção para verificação de esbeltez local (b/t).
    # Prioriza colunas explícitas h_mm e bf_mm do catálogo atualizado.
    h_mm = profile.get("h_mm", 50.0)
    bf_mm = profile.get("bf_mm", 50.0)
    t_mm = profile.get("t_mm", 3.0)
    
    # b_val para flexão Z (em torno do eixo horizontal) é a altura h.
    b_val = h_mm / 1000.0
    t_val = t_mm / 1000.0

    # Largura flat (descontando o raio de dobra aproximado).
    # Para seções I ou Ue, b_flat é h ou bf. Usamos a maior dimensão para ser conservador no Q.
    b_max = max(h_mm, bf_mm) / 1000.0
    b_flat = max(b_max - 3 * t_val, t_val)
    lamb = b_flat / t_val
    lamb_r = 1.40 * math.sqrt(E / (material["fy"] * 1e6))

    # Cálculo do Fator Q (Redução da seção eficaz por flambagem local).
    Qa = 1.0
    if lamb > lamb_r:
        # Largura efetiva simplificada conforme Anexo F da NBR 8800.
        bef = (
            1.92
            * t_val
            * math.sqrt(E / (material["fy"] * 1e6))
            * (1.0 - (0.38 / lamb) * math.sqrt(E / (material["fy"] * 1e6)))
        )
        bef = min(bef, b_flat)
        A_ef = A - 4 * (b_flat - bef) * t_val
        Qa = max(A_ef / A, 0.001)

    fy_comp = Qa * fy

    # -------------------------------------------------------------------------
    # CAPACIDADE AXIAL (N_rd)
    # -------------------------------------------------------------------------
    if force >= 0:
        # Tração Axial (N_rd = A * f_y / gamma_a1)
        N_rd = A * fy
    else:
        # Compressão Axial: Euler considerando o eixo crítico (maior lambda).
        nex = (math.pi**2 * E * profile["Ix_m4"]) / (lkx**2)
        ney = (math.pi**2 * E * profile["Iy_m4"]) / (lky**2)
        ne = min(nex, ney)
        lambda0 = math.sqrt((A * (material["fy"] * 1e6 * Qa)) / ne)
        # Redutor Chi por Flambagem Global.
        chi = 0.658 ** (lambda0**2) if lambda0 <= 1.5 else 0.877 / (lambda0**2)
        N_rd = chi * A * fy_comp

    N_sd = abs(force)

    # -------------------------------------------------------------------------
    # CAPACIDADE À FLEXÃO (M_rd) E INTERAÇÃO N + M
    # -------------------------------------------------------------------------
    # Aproximação elástica: M_rd = W * fy / gamma_a1.
    W_z = profile["Ix_m4"] / (b_val / 2)
    W_y = profile["Iy_m4"] / (bf_mm / 1000.0 / 2)
    M_zrd, M_yrd = W_z * fy, W_y * fy
    M_zsd, M_ysd = abs(mz), abs(my)

    if N_rd == 0:
        return 999.0
    
    ratio_N = N_sd / N_rd
    ratio_M = (M_zsd / M_zrd) + (M_ysd / M_yrd) if (M_zrd > 0 and M_yrd > 0) else 0.0

    # Equação de Interação para Esforços Combinados (NBR 8800 Item 5.5).
    if ratio_N >= 0.2:
        utilization = ratio_N + (8.0 / 9.0) * ratio_M
    else:
        utilization = (ratio_N / 2.0) + ratio_M

    return utilization


def calculate_lk_map(members_to_analyze, params):
    """
    Mapeamento do Comprimento Efetivo (Lk) para banzos.
    Conforme NBR 8800 itens 4.11/4.12: Transversais provêm contenção lateral
    se ancoradas por um sistema global de contraventamento.
    """
    braced_nodes = set()
    if params.raw_truss:
        for nid, node in params.raw_truss.nodes.items():
            if node.support != "None":
                braced_nodes.add(nid)
    else:
        n = params.divisions
        for bn in ["FL0", "BL0", f"FL{n}", f"BL{n}"]:
            braced_nodes.add(bn)

    for m in members_to_analyze:
        # Transversais (terças) e Contraventamentos agem como pontos de travamento lateral.
        if m["group"] in ["Transversal", "Contraventamento"]:
            braced_nodes.add(m["node_start"])
            braced_nodes.add(m["node_end"])

    chord_graph = {}
    for m in members_to_analyze:
        if m["group"] in ["Banzo Superior", "Banzo Inferior"]:
            n1, n2 = m["node_start"], m["node_end"]
            if n1 not in chord_graph:
                chord_graph[n1] = []
            if n2 not in chord_graph:
                chord_graph[n2] = []
            chord_graph[n1].append((n2, m["length"]))
            chord_graph[n2].append((n1, m["length"]))

    lk_map = {}
    for m in members_to_analyze:
        # Lky (In-plane) é sempre o comprimento da barra para treliças simples.
        lky = m["length"]
        
        if m["group"] in ["Banzo Superior", "Banzo Inferior"]:
            lkx = m["length"]
            # Varredura bidirecional no grafo de adjacência do banzo para Lkx.
            for start_node, other_node in [
                (m["node_start"], m["node_end"]),
                (m["node_end"], m["node_start"]),
            ]:
                curr, prev = start_node, other_node
                while curr not in braced_nodes:
                    neighbors = [
                        conn for conn in chord_graph.get(curr, []) if conn[0] != prev
                    ]
                    if not neighbors:
                        break
                    next_node, length = neighbors[0]
                    lkx += length
                    prev, curr = curr, next_node
            lk_map[m["id"]] = (lkx, lky)
        else:
            lk_map[m["id"]] = (m["length"], lky)
    return lk_map


def build_and_solve_truss(
    params: TrussRequest, profile_indices, profiles_catalog, material
):
    """
    Formulação FEA via Matriz de Rigidez Direta.
    Implementa envoltória NBR 8800 com separação de G1 (Self-weight) e G2 (External Dead).
    """
    model = FEModel3D()

    # Propriedades do Material.
    nu = 0.3
    G = (material["E"] * 1e9) / (2 * (1 + nu))
    model.add_material(
        material["name"], material["E"] * 1e9, G, nu, material["rho"] * 1e-9
    )

    for p in profiles_catalog:
        if p["Name"] not in model.sections:
            model.add_section(p["Name"], p["Area_m2"], p["Ix_m4"], p["Iy_m4"], p["J_m4"])

    nodes_coords = {}
    members_to_analyze = []
    support_nodes_x = []

    # Winkler-Terzaghi foundations.
    soil = SOIL_DATABASE.get(params.soil_type, SOIL_DATABASE["Rocha"])
    ks_nominal = (
        params.custom_ks
        if (params.soil_type == "Customizado" and params.custom_ks is not None)
        else soil["ks1"]
    )
    B = max(params.footing_b, 0.305)
    L_footing = params.footing_l
    ks_real = ks_nominal
    if soil["type"] == "granular":
        ks_real = ks_nominal * ((B + 0.305) / (2 * B)) ** 2
    elif soil["type"] == "coesivo":
        ks_real = ks_nominal * (0.305 / B)
    
    K_z = (ks_real * B * L_footing) * 1000
    I_x_soil = (L_footing * B**3) / 12
    I_z_soil = (B * L_footing**3) / 12
    K_theta_x = (ks_real * I_x_soil) * 1000
    K_theta_z = (ks_real * I_z_soil) * 1000

    def add_truss_member_to_model(m_id, n1, n2, group, length):
        p_idx = profile_indices.get(group, profile_indices.get("Padrão", 0))
        profile = profiles_catalog[p_idx]
        members_to_analyze.append(
            {
                "id": m_id,
                "node_start": n1,
                "node_end": n2,
                "group": group,
                "length": length,
                "profile": profile["Name"],
                "area": profile["Area_m2"],
                "unit_weight": profile["Area_m2"] * material["rho"],
            }
        )
        mid_str = f"M{m_id}"
        model.add_member(mid_str, n1, n2, material["name"], profile["Name"])
        # Removidas liberações para garantir estabilidade numérica absoluta (Matrix singularity).
        # Em treliças de banzos contínuos, os esforços axiais permanecem dominantes.

    if params.raw_truss:
        for nid, node in params.raw_truss.nodes.items():
            nodes_coords[nid] = (node.x, node.y, node.z)
            model.add_node(nid, node.x, node.y, node.z)
            if node.support != "None":
                support_nodes_x.append(node.x)
                if node.support == "Pinned":
                    model.def_support(nid, True, True, True, False, False, False)
                elif node.support == "Roller":
                    model.def_support(nid, False, True, True, False, False, False)
                elif node.support == "Fixed":
                    model.def_support(nid, True, True, True, True, True, True)

        for m in params.raw_truss.members:
            n1_coords, n2_coords = nodes_coords[m.node_start], nodes_coords[m.node_end]
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(n1_coords, n2_coords)))
            if dist < 0.001: continue
            add_truss_member_to_model(m.id, m.node_start, m.node_end, m.group, dist)
    else:
        L_gen, H, W, n = params.length, params.height, params.width, params.divisions
        dx = L_gen / n
        for i in range(n + 1):
            x = i * dx
            for side, z in [("F", 0), ("B", W)]:
                nid = f"{side}L{i}"
                model.add_node(nid, x, 0, z)
                nodes_coords[nid] = (x, 0, z)
                uid = f"{side}U{i}"
                model.add_node(uid, x, H, z)
                nodes_coords[uid] = (x, H, z)
            
                # Apoios da treliça paramétrica.
                if i == 0 or i == n:
                    support_nodes_x.append(x)
                    if i == 0:
                        model.def_support(nid, True, True, True, False, False, False)
                    else:
                        model.def_support(nid, False, True, True, False, False, False)

        for i in range(n):
            for side in ["F", "B"]:
                add_truss_member_to_model(len(members_to_analyze), f"{side}L{i}", f"{side}L{i+1}", "Banzo Inferior", dx)
                add_truss_member_to_model(len(members_to_analyze), f"{side}U{i}", f"{side}U{i+1}", "Banzo Superior", dx)
                add_truss_member_to_model(len(members_to_analyze), f"{side}L{i}", f"{side}U{i}", "Montante", H)
                
                # Diagonais Howe (Compressão center-top)
                if i < n / 2:
                    add_truss_member_to_model(len(members_to_analyze), f"{side}L{i}", f"{side}U{i+1}", "Diagonal", math.sqrt(dx**2 + H**2))
                else:
                    add_truss_member_to_model(len(members_to_analyze), f"{side}L{i+1}", f"{side}U{i}", "Diagonal", math.sqrt(dx**2 + H**2))
            
            # Travamentos transversais em TODOS os nós para estabilidade 3D.
            add_truss_member_to_model(len(members_to_analyze), f"FL{i}", f"BL{i}", "Transversal", W)
            add_truss_member_to_model(len(members_to_analyze), f"FU{i}", f"BU{i}", "Transversal", W)
            
            # Contraventamentos espaçados (a cada 2 painéis) para teste de Lkx.
            if i % 2 == 0:
                dist_x = math.sqrt(dx**2 + W**2)
                add_truss_member_to_model(len(members_to_analyze), f"FL{i}", f"BL{i+1}", "Contraventamento", dist_x)
                add_truss_member_to_model(len(members_to_analyze), f"BL{i}", f"FL{i+1}", "Contraventamento", dist_x)

        # Últimos montantes e travamentos.
        for side in ["F", "B"]:
            add_truss_member_to_model(len(members_to_analyze), f"{side}L{n}", f"{side}U{n}", "Montante", H)
        add_truss_member_to_model(len(members_to_analyze), f"FL{n}", f"BL{n}", "Transversal", W)
        add_truss_member_to_model(len(members_to_analyze), f"FU{n}", f"BU{n}", "Transversal", W)

    # Cálculo dinâmico do vão real (L) para verificação ELS.
    real_span = (max(support_nodes_x) - min(support_nodes_x)) if support_nodes_x else params.length
    real_span = max(real_span, 0.1)

    # Processamento de Cargas da API (G2 e Q).
    max_y = max(c[1] for c in nodes_coords.values())
    target_top_nodes = [n for n, c in nodes_coords.items() if c[1] >= max_y - 0.05]
    
    for lc in params.load_cases:
        case_name = "Dead2" if lc.type == "G" else "Live"
        nodes_to_load = lc.nodes if lc.nodes else target_top_nodes
        if not nodes_to_load: continue
        
        # Rateio simplificado para cargas sem nós específicos.
        load_per_node = lc.value / len(nodes_to_load)
        for nid in nodes_to_load:
            if nid in nodes_coords:
                model.add_node_load(nid, lc.direction, load_per_node, case=case_name)

    # Acúmulo de Água (NBR 6120 Item 5.6) - Tratado como G2 adicional (Ação Especial).
    if params.water_lamina > 0:
        # Peso d'água = lamina (mm) * 10 N/m2 por mm (1000 kg/m3).
        water_load_n = (params.water_lamina * 10.0) * (params.length * params.width)
        load_per_node_w = water_load_n / len(target_top_nodes)
        for nid in target_top_nodes:
            model.add_node_load(nid, "FY", -load_per_node_w, case="Dead2")

    # G1: Peso Próprio recalculado.
    total_weight = 0
    node_weights_dead1 = {node: 0.0 for node in nodes_coords}
    for m in members_to_analyze:
        w = m["unit_weight"] * m["length"]
        total_weight += w
        node_weights_dead1[m["node_start"]] += w / 2
        node_weights_dead1[m["node_end"]] += w / 2

    for node, weight in node_weights_dead1.items():
        model.add_node_load(node, "FY", -weight * 9.81, case="Dead1")

    # Combinações NBR 8800.
    model.add_load_combo("ELU_Normal", {"Dead1": 1.25, "Dead2": 1.40, "Live": 1.50})
    model.add_load_combo("ELU_Secundario", {"Dead1": 1.25, "Dead2": 1.40, "Live": 1.40})
    model.add_load_combo("ELU_Alivio", {"Dead1": 1.00, "Dead2": 1.00, "Live": 1.50})
    model.add_load_combo("ELS_Flecha", {"Dead1": 1.00, "Dead2": 1.00, "Live": 1.00})

    elu_combos = ["ELU_Normal", "ELU_Secundario", "ELU_Alivio"]

    # NBR 6120 Item 6.4: Carga Concentrada de Manutenção (1 kN isolada).
    # Criamos uma combinação para cada nó do banzo superior para extrair o pior caso local.
    for i, nid in enumerate(target_top_nodes):
        maint_case = f"Maint_{i}"
        model.add_node_load(nid, "FY", -1000.0, case=maint_case)
        maint_combo = f"ELU_Maint_{i}"
        model.add_load_combo(maint_combo, {"Dead1": 1.25, "Dead2": 1.40, maint_case: 1.50})
        elu_combos.append(maint_combo)

    try:
        model.analyze(check_statics=True, log=False)
    except Exception as e:
        return [], {}, {"_ERROR_": f"Falha na análise: {str(e)}"}, 0.0, 0.0, 0.0

    # Extração da Flecha Máxima (ELS) e Contra-flecha (Item 10.2 NBR 8800).
    max_flecha = 0.0
    max_precamber = 0.0
    model.add_load_combo("ELS_Permanente", {"Dead1": 1.00, "Dead2": 1.00})
    try:
        model.analyze(check_statics=False, log=False)
    except:
        pass

    for nid, node in model.nodes.items():
        dy = abs(node.DY.get("ELS_Flecha", 0.0))
        if dy > max_flecha:
            max_flecha = dy
        dy_p = abs(node.DY.get("ELS_Permanente", 0.0))
        if dy_p > max_precamber:
            max_precamber = dy_p

    # Verificação de instabilidade por deslocamento excessivo.
    if max_flecha > 2.0:  # 2 metros é um limite de segurança para divergência.
        return [], {}, {"_ERROR_": "A estrutura apresentou deslocamento excessivo (instabilidade)."}, 0.0, 0.0, 0.0, 0.0

    lk_map = calculate_lk_map(members_to_analyze, params)
    member_results = []
    max_u_per_group = {}

    for m in members_to_analyze:
        mid_str = f"M{m['id']}"
        # Envoltória de esforços axiais e momentos fletores.
        axial_forces = [model.members[mid_str].max_axial(c) for c in elu_combos] + [
            model.members[mid_str].min_axial(c) for c in elu_combos
        ]
        axial_f = max(axial_forces, key=abs)

        my_forces = [model.members[mid_str].max_moment("My", c) for c in elu_combos] + [
            model.members[mid_str].min_moment("My", c) for c in elu_combos
        ]
        my_f = max(my_forces, key=abs)

        mz_forces = [model.members[mid_str].max_moment("Mz", c) for c in elu_combos] + [
            model.members[mid_str].min_moment("Mz", c) for c in elu_combos
        ]
        mz_f = max(mz_forces, key=abs)

        if math.isnan(axial_f) or math.isinf(axial_f):
            return [], {}, {"_ERROR_": "Divergência numérica nos esforços."}, 0.0, 0.0, 0.0, 0.0

        p_idx = profile_indices.get(m["group"], profile_indices.get("Padrão", 0))
        profile = profiles_catalog[p_idx]
        lkx, lky = lk_map[m["id"]]
        u = calculate_max_utilization(
            axial_f, mz_f, my_f, profile, m["length"], material, m["group"], lkx, lky
        )

        if m["group"] not in max_u_per_group or u > max_u_per_group[m["group"]]:
            max_u_per_group[m["group"]] = u

        member_results.append(MemberResult(
            id=m["id"], node_start=m["node_start"], node_end=m["node_end"],
            group=m["group"], profile=profile["Name"], axial_force=float(axial_f),
            utilization=float(u), stress_type="Tração" if axial_f > 0 else "Compressão"
        ))

    nodes_results = {}
    for nid, c in nodes_coords.items():
        sup = params.raw_truss.nodes[nid].support if (params.raw_truss and nid in params.raw_truss.nodes) else "None"
        nodes_results[nid] = NodeResult(id=nid, x=c[0], y=c[1], z=c[2], support=sup)

    return member_results, nodes_results, max_u_per_group, total_weight, max_flecha, real_span, max_precamber
