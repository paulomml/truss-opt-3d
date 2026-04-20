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


def calculate_max_utilization(force, profile, length, material):
    """
    Determina a Taxa de Utilização (U) conforme NBR 8800.
    Justificativa: Métrica base para o algoritmo guloso de upscaling de seções no orquestrador.
    """
    fy = (
        material["fy"] * 1e6
    )  # Conversão de MPa para Pa para compatibilidade com o solver.
    E = material["E"] * 1e9  # Módulo de elasticidade convertido para Pa.
    A = profile["Area"]
    I = profile["Ix"]

    # O índice de esbeltez (lambda) governa o fator de redução chi em membros comprimidos.
    r = math.sqrt(I / A)
    slenderness = length / r
    ne = (math.pi**2 * E * I) / (length**2)

    if force >= 0:
        # Tração axial: limite de escoamento da seção bruta.
        capacity = A * fy
    else:
        # Compressão: Aplica fator de redução (chi) via curva de flambagem de Euler-NBR8800.
        f_abs = abs(force)
        lambda0 = math.sqrt((A * fy) / ne)
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

    # Definição das características do material.
    model.add_material(
        material["name"], material["E"] * 1e9, 77e9, 0.3, material["rho"] * 1e-9
    )

    # Cache local de seções transversais para evitar redundância na montagem da matriz [K].
    for p in profiles_catalog:
        if p["Name"] not in model.sections:
            model.add_section(p["Name"], p["Area"], p["Ix"], p["Ix"], 1e-4)

    nodes_coords = {}
    members_to_analyze = []

    # Mitiga o erro de escala do ensaio de placa para fundações reais via Winkler-Terzaghi.
    soil = SOIL_DATABASE.get(params.soil_type, SOIL_DATABASE["Rocha"])
    ks_nominal = (
        params.custom_ks
        if (params.soil_type == "Customizado" and params.custom_ks is not None)
        else soil["ks1"]
    )

    B = max(params.footing_b, 0.305)
    L_footing = params.footing_l

    if soil["type"] == "granular":
        # Ajuste geométrico para solos com comportamento granular.
        # A rigidez do subleito é ponderada pelas dimensões reais da sapata.
        ks_real = ks_nominal * ((B + 0.305) / (2 * B)) ** 2
    elif soil["type"] == "coesivo":
        # Redução do coeficiente ks para considerar a influência da largura da base em solos argilosos.
        # Previne recalques excessivos por adensamento lateral.
        ks_real = ks_nominal * (0.305 / B)
    else:
        ks_real = ks_nominal

    # Rigidez de mola equivalente (K_z, K_theta) para modelagem de base elástica (Solo).
    K_z = (ks_real * B * L_footing) * 1000

    # Definição do engastamento elástico rotacional para modelagem precisa da interação solo-estrutura.
    I_x = (L_footing * B**3) / 12
    I_z = (B * L_footing**3) / 12
    K_theta_x = (ks_real * I_x) * 1000
    K_theta_z = (ks_real * I_z) * 1000

    if params.raw_truss:
        # Injeção da topologia customizada recebida via payload.
        for nid, node in params.raw_truss.nodes.items():
            nodes_coords[nid] = (node.x, node.y, node.z)
            model.add_node(nid, node.x, node.y, node.z)

            if node.support != "None":
                if node.support in ["Pinned", "Roller"]:
                    # Apoio elástico: Combina restrições rígidas com molas de solo (Winkler).
                    model.def_support(
                        nid, True, False, True, False, True, False
                    )  # Restrição em X, Z e rotação em Y.
                    model.def_support_spring(nid, "DY", K_z)
                    model.def_support_spring(nid, "RX", K_theta_x)
                    model.def_support_spring(nid, "RZ", K_theta_z)
                elif node.support == "Fixed":
                    model.def_support(nid, True, True, True, True, True, True)

        for m in params.raw_truss.members:
            n1, n2 = nodes_coords[m.node_start], nodes_coords[m.node_end]
            dist = math.sqrt(
                (n1[0] - n2[0]) ** 2 + (n1[1] - n2[1]) ** 2 + (n1[2] - n2[2]) ** 2
            )

            # Prevenção de singularidade na matriz de rigidez global.
            if dist < 0.001:
                continue

            p_idx = profile_indices.get(m.group, profile_indices.get("Padrão", 0))
            profile = profiles_catalog[p_idx]

            members_to_analyze.append(
                {
                    "id": m.id,
                    "node_start": m.node_start,
                    "node_end": m.node_end,
                    "group": m.group,
                    "length": dist,
                    "profile": profile["Name"],
                    "area": profile["Area"],
                    "inertia": profile["Ix"],
                    "unit_weight": profile["Area"] * material["rho"],
                }
            )
            model.add_member(
                f"M{m.id}", m.node_start, m.node_end, material["name"], profile["Name"]
            )
    else:
        # Factory de topologias paramétricas padrão (Fallback para modelos built-in).
        L, H, W, n = params.length, params.height, params.width, params.divisions
        dx = L / n

        def add_node(nid, x, y, z):
            nodes_coords[nid] = (x, y, z)
            model.add_node(nid, x, y, z)

        for i in range(n + 1):
            x = i * dx
            add_node(f"FL{i}", x, 0, 0)
            add_node(f"BL{i}", x, 0, W)
            add_node(f"FU{i}", x, H, 0)
            add_node(f"BU{i}", x, H, W)

        def add_truss_member(n1, n2, group):
            p1, p2 = nodes_coords[n1], nodes_coords[n2]
            dist = math.sqrt(
                (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2
            )

            # Validação geométrica: barras sem rigidez axial são descartadas para evitar erros de divisão por zero.
            if dist < 0.001:
                return

            mid = len(members_to_analyze)
            p_idx = profile_indices.get(group, profile_indices.get("Padrão", 0))
            profile = profiles_catalog[p_idx]
            members_to_analyze.append(
                {
                    "id": mid,
                    "node_start": n1,
                    "node_end": n2,
                    "group": group,
                    "length": dist,
                    "profile": profile["Name"],
                    "area": profile["Area"],
                    "inertia": profile["Ix"],
                    "unit_weight": profile["Area"] * material["rho"],
                }
            )
            model.add_member(f"M{mid}", n1, n2, material["name"], profile["Name"])

        for i in range(n):
            for side in ["F", "B"]:
                add_truss_member(f"{side}L{i}", f"{side}L{i+1}", "Banzo Inferior")
                add_truss_member(f"{side}U{i}", f"{side}U{i+1}", "Banzo Superior")
                add_truss_member(f"{side}L{i}", f"{side}U{i}", "Montante")
                add_truss_member(f"{side}L{i}", f"{side}U{i+1}", "Diagonal")
            add_truss_member(f"FL{i}", f"BL{i}", "Transversal")
            add_truss_member(f"FU{i}", f"BU{i}", "Transversal")

        # Restrições de base elástica para simular fundação direta via Winkler.
        base_nodes = ["FL0", "BL0", f"FL{n}", f"BL{n}"]
        for bn in base_nodes:
            model.def_support(bn, True, False, True, False, True, False)
            model.def_support_spring(bn, "DY", K_z)
            model.def_support_spring(bn, "RX", K_theta_x)
            model.def_support_spring(bn, "RZ", K_theta_z)

    # Rateio de carga vertical via área de influência nodal (Q). Simula carregamento distribuído de deck/telhado.
    total_force_n = params.total_load * 9.81
    max_y = max(c[1] for c in nodes_coords.values())
    top_nodes = [
        node
        for node, coords in nodes_coords.items()
        if coords[1] >= max_y - 0.05 and coords[1] > 0.01
    ]
    if top_nodes:
        f_per_node = total_force_n / len(top_nodes)
        for node_id in top_nodes:
            model.add_node_load(node_id, "FY", -f_per_node, case="External")

    total_weight = 0
    node_weights = {node: 0.0 for node in nodes_coords}
    for m in members_to_analyze:
        w = m["unit_weight"] * m["length"]
        total_weight += w
        node_weights[m["node_start"]] += w / 2
        node_weights[m["node_end"]] += w / 2

    for node, weight in node_weights.items():
        model.add_node_load(node, "FY", -weight * 9.81, case="Dead")

    # Superposição de efeitos (Combinação de Cargas). LC1 = Permanente (G) + Variável (Q).

    try:
        model.analyze(check_statics=True, log=False)
    except Exception as e:
        # Fallback para erros de convergência ou instabilidade de primeira ordem.
        return [], {}, {"_ERROR_": str(e)}, 0.0

    member_results = []
    max_u_per_group = {}
    for m in members_to_analyze:
        mid = f"M{m['id']}"
        # Extração de esforços axiais via Pynite. 
        # Trade-off: Consideramos apenas o esforço crítico da envoltória por barra.
        f_max = model.members[mid].max_axial("LC1")
        f_min = model.members[mid].min_axial("LC1")

        if (
            math.isnan(f_max)
            or math.isinf(f_max)
            or math.isnan(f_min)
            or math.isinf(f_min)
        ):
            # Catch de instabilidade numérica (Singularity/Zero-pivot) na inversão de [K].
            return (
                [],
                {},
                {
                    "_ERROR_": "Instabilidade numérica detectada durante a inversão da matriz de rigidez."
                },
                0.0,
            )

        axial_f = f_max if abs(f_max) > abs(f_min) else f_min

        p_idx = profile_indices.get(m["group"], profile_indices.get("Padrão", 0))
        profile = profiles_catalog[p_idx]
        u = calculate_max_utilization(axial_f, profile, m["length"], material)
        group = m["group"]
        if group not in max_u_per_group or u > max_u_per_group[group]:
            max_u_per_group[group] = u
        member_results.append(
            MemberResult(
                id=m["id"],
                node_start=m["node_start"],
                node_end=m["node_end"],
                group=m["group"],
                profile=m["profile"],
                axial_force=float(axial_f),
                utilization=float(u),
                stress_type=(
                    "Tração"
                    if axial_f > 0.01
                    else ("Compressão" if axial_f < -0.01 else "Nenhum")
                ),
            )
        )

    nodes_results = {}
    for nid, c in nodes_coords.items():
        sup = "None"
        if params.raw_truss and nid in params.raw_truss.nodes:
            sup = params.raw_truss.nodes[nid].support
        elif nid in ["FL0", "BL0", f"FL{params.divisions}", f"BL{params.divisions}"]:
            sup = "Pinned"
        nodes_results[nid] = NodeResult(id=nid, x=c[0], y=c[1], z=c[2], support=sup)

    return member_results, nodes_results, max_u_per_group, total_weight
