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


def calculate_max_utilization(force, profile, length, material, group_name="Padrão", l_effective=None):
    """
    Determina a Taxa de Utilização (U) conforme NBR 8800.
    Justificativa: Métrica base para o algoritmo guloso de upscaling de seções no orquestrador.
    Inclui coeficientes de minoração da resistência e limites de esbeltez normativa.
    """
    gamma_a1 = 1.10  # Coeficiente de minoração da resistência ao escoamento (NBR 8800).
    fy = (material["fy"] * 1e6) / gamma_a1
    E = material["E"] * 1e9
    A = profile["Area"]
    
    # Justificativa: A flambagem ocorre no eixo de menor inércia.
    I_min = min(profile["Ix"], profile["Iy"])
    r_min = math.sqrt(I_min / A)
    
    # L_k pode ser maior que o comprimento da barra para banzos sem travamento transversal.
    lk = l_effective if l_effective is not None else length
    slenderness = lk / r_min

    # Verificação de limites de esbeltez normativa (NBR 8800: item 5.2.8 e 5.3.4).
    # Trade-off: Penalização severa (U=999) para forçar o upscaling imediato da seção.
    if force < -0.01 and slenderness > 200:
        return 999.0  # Limite para compressão.
    if force >= -0.01 and slenderness > 300:
        return 999.0  # Limite para tração.

    if force >= 0:
        # Tração axial: N_rd = A * fy / gamma_a1 (já aplicado no fy).
        capacity = A * fy
    else:
        # Compressão: Euler + Coeficiente de Redução Chi.
        ne = (math.pi**2 * E * I_min) / (lk**2)
        lambda0 = math.sqrt((A * (material["fy"] * 1e6)) / ne)
        if lambda0 <= 1.5:
            chi = 0.658 ** (lambda0**2)
        else:
            chi = 0.877 / (lambda0**2)
        capacity = chi * A * fy

    return abs(force) / capacity


def build_and_solve_truss(
    params: TrussRequest, profile_indices, profiles_catalog, material
):
    """
    Formulação FEA via Matriz de Rigidez Direta.
    Resolve [K]{u} = {F} para extração de esforços críticos da envoltória.
    """
    model = FEModel3D()

    # Justificativa: G calculado via relação elástica isotrópica G = E / (2 * (1 + nu)).
    nu = 0.3
    G = (material["E"] * 1e9) / (2 * (1 + nu))
    model.add_material(
        material["name"], material["E"] * 1e9, G, nu, material["rho"] * 1e-9
    )

    # Cache local de seções transversais. Iy e J consumidos do catálogo.
    for p in profiles_catalog:
        if p["Name"] not in model.sections:
            model.add_section(p["Name"], p["Area"], p["Ix"], p["Iy"], p["J"])

    nodes_coords = {}
    members_to_analyze = []

    # Winkler-Terzaghi foundations setup...
    soil = SOIL_DATABASE.get(params.soil_type, SOIL_DATABASE["Rocha"])
    ks_nominal = (
        params.custom_ks
        if (params.soil_type == "Customizado" and params.custom_ks is not None)
        else soil["ks1"]
    )
    B = max(params.footing_b, 0.305)
    L_footing = params.footing_l
    if soil["type"] == "granular":
        ks_real = ks_nominal * ((B + 0.305) / (2 * B)) ** 2
    elif soil["type"] == "coesivo":
        ks_real = ks_nominal * (0.305 / B)
    else:
        ks_real = ks_nominal
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
                "area": profile["Area"],
                "unit_weight": profile["Area"] * material["rho"],
            }
        )
        mid_str = f"M{m_id}"
        model.add_member(mid_str, n1, n2, material["name"], profile["Name"])
        
        # Justificativa: A liberação total em barras colineares (banzos) gera instabilidade de translação (mecanismo).
        # Mantemos a continuidade nos banzos para estabilizar nós intermediários e fixamos Rx para evitar instabilidade rotacional.
        if group in ["Banzo Superior", "Banzo Inferior"]:
            model.def_releases(mid_str, Ryi=False, Rzi=False, Ryj=True, Rzj=True)
        else:
            model.def_releases(mid_str, Ryi=True, Rzi=True, Ryj=True, Rzj=True)

    if params.raw_truss:
        for nid, node in params.raw_truss.nodes.items():
            nodes_coords[nid] = (node.x, node.y, node.z)
            model.add_node(nid, node.x, node.y, node.z)
            if node.support != "None":
                if node.support == "Pinned":
                    model.def_support(nid, True, False, True, False, True, False)
                    model.def_support_spring(nid, "DY", K_z)
                    model.def_support_spring(nid, "RX", K_theta_x)
                    model.def_support_spring(nid, "RZ", K_theta_z)
                elif node.support == "Roller":
                    # Justificativa: Roller deve permitir translação em X para evitar tensões parasitas.
                    model.def_support(nid, False, False, True, False, True, False)
                    model.def_support_spring(nid, "DY", K_z)
                elif node.support == "Fixed":
                    model.def_support(nid, True, True, True, True, True, True)

        for m in params.raw_truss.members:
            n1, n2 = nodes_coords[m.node_start], nodes_coords[m.node_end]
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(n1, n2)))
            if dist < 0.001: continue
            add_truss_member_to_model(m.id, m.node_start, m.node_end, m.group, dist)
    else:
        L, H, W, n = params.length, params.height, params.width, params.divisions
        dx = L / n
        for i in range(n + 1):
            x = i * dx
            model.add_node(f"FL{i}", x, 0, 0); nodes_coords[f"FL{i}"] = (x, 0, 0)
            model.add_node(f"BL{i}", x, 0, W); nodes_coords[f"BL{i}"] = (x, 0, W)
            model.add_node(f"FU{i}", x, H, 0); nodes_coords[f"FU{i}"] = (x, H, 0)
            model.add_node(f"BU{i}", x, H, W); nodes_coords[f"BU{i}"] = (x, H, W)

        for i in range(n):
            for side in ["F", "B"]:
                dist_h = dx
                add_truss_member_to_model(len(members_to_analyze), f"{side}L{i}", f"{side}L{i+1}", "Banzo Inferior", dist_h)
                add_truss_member_to_model(len(members_to_analyze), f"{side}U{i}", f"{side}U{i+1}", "Banzo Superior", dist_h)
                add_truss_member_to_model(len(members_to_analyze), f"{side}L{i}", f"{side}U{i}", "Montante", H)
                dist_d = math.sqrt(dx**2 + H**2)
                add_truss_member_to_model(len(members_to_analyze), f"{side}L{i}", f"{side}U{i+1}", "Diagonal", dist_d)
            
            # Justificativa: Travamento transversal e Contraventamento em X para estabilidade 3D.
            add_truss_member_to_model(len(members_to_analyze), f"FL{i}", f"BL{i}", "Transversal", W)
            add_truss_member_to_model(len(members_to_analyze), f"FU{i}", f"BU{i}", "Transversal", W)
            # Diagonais de contraventamento (X-Bracing)
            dist_x = math.sqrt(dx**2 + W**2)
            add_truss_member_to_model(len(members_to_analyze), f"FL{i}", f"BL{i+1}", "Contraventamento", dist_x)
            add_truss_member_to_model(len(members_to_analyze), f"BL{i}", f"FL{i+1}", "Contraventamento", dist_x)
            add_truss_member_to_model(len(members_to_analyze), f"FU{i}", f"BU{i+1}", "Contraventamento", dist_x)
            add_truss_member_to_model(len(members_to_analyze), f"BU{i}", f"FU{i+1}", "Contraventamento", dist_x)

        # Fechamento do último quadro transversal.
        add_truss_member_to_model(len(members_to_analyze), f"FL{n}", f"BL{n}", "Transversal", W)
        add_truss_member_to_model(len(members_to_analyze), f"FU{n}", f"BU{n}", "Transversal", W)

        for bn in ["FL0", "BL0", f"FL{n}", f"BL{n}"]:
            model.def_support(bn, True, False, True, False, True, False)
            model.def_support_spring(bn, "DY", K_z)
            model.def_support_spring(bn, "RX", K_theta_x)
            model.def_support_spring(bn, "RZ", K_theta_z)

    # Justificativa: Heurística de posição de carga baseada na tipologia (Bridge vs Roof).
    is_bridge = any("bridge" in (m["group"] or "").lower() for m in members_to_analyze)
    total_force_n = params.total_load * 9.81
    
    if is_bridge:
        target_nodes = [n for n, c in nodes_coords.items() if c[1] < 0.05]
    else:
        max_y = max(c[1] for c in nodes_coords.values())
        target_nodes = [n for n, c in nodes_coords.items() if c[1] >= max_y - 0.05]

    if target_nodes:
        # Justificativa: Rateio de cargas por área de influência.
        # Para treliças longitudinais (com banzos), os nós de extremidade recebem 50% simulando carga distribuída.
        # Para torres (sem banzos), a carga no topo é concentrada e rateada igualmente entre os montantes.
        has_banzos = any("banzo" in (m["group"] or "").lower() for m in members_to_analyze)
        min_x = min(nodes_coords[n][0] for n in target_nodes)
        max_x = max(nodes_coords[n][0] for n in target_nodes)
        node_weights = {}
        total_influence = 0
        for n in target_nodes:
            x = nodes_coords[n][0]
            if has_banzos:
                weight = 0.5 if (abs(x - min_x) < 0.01 or abs(x - max_x) < 0.01) else 1.0
            else:
                weight = 1.0
            node_weights[n] = weight
            total_influence += weight
        
        load_unit = total_force_n / total_influence
        for n, w in node_weights.items():
            model.add_node_load(n, "FY", -load_unit * w, case="External")

    total_weight = 0
    node_weights_dead = {node: 0.0 for node in nodes_coords}
    for m in members_to_analyze:
        w = m["unit_weight"] * m["length"]
        total_weight += w
        node_weights_dead[m["node_start"]] += w / 2
        node_weights_dead[m["node_end"]] += w / 2

    for node, weight in node_weights_dead.items():
        model.add_node_load(node, "FY", -weight * 9.81, case="Dead")

    # Justificativa: Combinação de ELU conforme NBR 8800 (1.4 para ações permanentes e variáveis).
    model.add_load_combo("LC1", {"External": 1.4, "Dead": 1.4})

    try:
        model.analyze(check_statics=True, log=False)
        
        # Justificativa: Falhas de solo (ks=0) podem não gerar matriz singular perfeita, mas causam deslocamentos astronômicos.
        for nid, node in model.nodes.items():
            if hasattr(node, 'DY') and isinstance(node.DY, dict):
                dy = node.DY.get("LC1", 0)
                if abs(dy) > 1.0:
                    return [], {}, {"_ERROR_": f"Instabilidade severa (deslocamento excessivo no nó {nid})."}, 0.0
                    
    except Exception as e:
        return [], {}, {"_ERROR_": str(e)}, 0.0

    # Heurística de Lk (Comprimento Efetivo) para banzos.
    # Justificativa: O comprimento de flambagem no eixo fraco é a distância entre travamentos transversais.
    lk_map = {}
    transversal_nodes = set()
    for m in members_to_analyze:
        if m["group"] in ["Transversal", "Contraventamento"]:
            transversal_nodes.add(m["node_start"])
            transversal_nodes.add(m["node_end"])

    for m in members_to_analyze:
        if m["group"] in ["Banzo Superior", "Banzo Inferior"]:
            # Simplificação: se os dois nós estão travados, Lk = L. Caso contrário, busca-se o próximo travamento.
            lk_map[m["id"]] = m["length"] # Heurística básica: assumindo travamento em cada nó após item 10.
        else:
            lk_map[m["id"]] = m["length"]

    member_results = []
    max_u_per_group = {}
    for m in members_to_analyze:
        mid_str = f"M{m['id']}"
        f_max = model.members[mid_str].max_axial("LC1")
        f_min = model.members[mid_str].min_axial("LC1")
        axial_f = f_max if abs(f_max) > abs(f_min) else f_min
        
        if math.isnan(axial_f) or math.isinf(axial_f):
            return [], {}, {"_ERROR_": "Divergência numérica."}, 0.0

        p_idx = profile_indices.get(m["group"], profile_indices.get("Padrão", 0))
        profile = profiles_catalog[p_idx]
        u = calculate_max_utilization(axial_f, profile, m["length"], material, m["group"], lk_map[m["id"]])
        
        if m["group"] not in max_u_per_group or u > max_u_per_group[m["group"]]:
            max_u_per_group[m["group"]] = u
            
        member_results.append(MemberResult(
            id=m["id"], node_start=m["node_start"], node_end=m["node_end"],
            group=m["group"], profile=profile["Name"], axial_force=float(axial_f),
            utilization=float(u), stress_type="Tração" if axial_f > 0 else "Compressão"
        ))

    nodes_results = {}
    for nid, c in nodes_coords.items():
        # Justificativa: O repasse explícito da condição de contorno (support) é indispensável para a correta renderização geométrica das sapatas na camada de visualização.
        sup = params.raw_truss.nodes[nid].support if (params.raw_truss and nid in params.raw_truss.nodes) else "None"
        nodes_results[nid] = NodeResult(id=nid, x=c[0], y=c[1], z=c[2], support=sup)

    return member_results, nodes_results, max_u_per_group, total_weight
