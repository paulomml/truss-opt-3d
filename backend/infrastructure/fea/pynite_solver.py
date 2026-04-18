import numpy as np
from Pynite import FEModel3D
from domain.models import TrussRequest, NodeResult, MemberResult
import math

# Parâmetros geotécnicos para o coeficiente de reação do subleito (ks1), referenciados ao ensaio de placa de 30,5 cm conforme bibliografia clássica de Terzaghi.
SOIL_DATABASE = {
    "Areia Fofa": {"ks1": 15000, "type": "granular"},
    "Areia Compacta": {"ks1": 100000, "type": "granular"},
    "Argila Mole": {"ks1": 10000, "type": "coesivo"},
    "Argila Rija": {"ks1": 40000, "type": "coesivo"},
    "Rocha": {"ks1": 250000, "type": "rigid"},
}


def calculate_max_utilization(force, profile, length, material):
    """
    Avaliação do Estado Limite Último (ELU) conforme preceitos da NBR 8800.
    Logo, a função determina o quociente entre a solicitação axial de cálculo e a resistência de projeto da seção.
    """
    fy = (
        material["fy"] * 1e6
    )  # Conversão de MPa para Pa para compatibilidade com o solver.
    E = material["E"] * 1e9  # Módulo de elasticidade convertido para Pa.
    A = profile["Area"]
    I = profile["Ix"]

    # Determinação do índice de esbeltez para avaliação de instabilidade global e flambagem.
    r = math.sqrt(I / A)
    slenderness = length / r
    ne = (math.pi**2 * E * I) / (length**2)

    if force >= 0:
        # Verificação da capacidade resistente sob esforço de tração axial simples.
        # Portanto, a resistência é limitada pela área bruta e a tensão de escoamento.
        capacity = A * fy
    else:
        # Dimensionamento à compressão: consideração da flambagem elástica de Euler.
        # Sendo assim, aplica-se o fator de redução por instabilidade baseado na esbeltez.
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
    Formulação do modelo discreto via Método dos Elementos Finitos (MEF) para resolução do sistema matricial.
    Sendo assim, o modelo processa a rigidez global e retorna os estados de tensão e deformação.
    """
    model = FEModel3D()

    # Definição das propriedades constitutivas do material para integração na matriz de rigidez global.
    model.add_material(
        material["name"], material["E"] * 1e9, 77e9, 0.3, material["rho"] * 1e-9
    )

    # Atribuição das propriedades geométricas das seções transversais (área e momentos de inércia) ao modelo.
    for p in profiles_catalog:
        if p["Name"] not in model.sections:
            model.add_section(p["Name"], p["Area"], p["Ix"], p["Ix"], 1e-4)

    nodes_coords = {}
    members_to_analyze = []

    # Correção do coeficiente de recalque para fundações reais via método de Winkler-Terzaghi.
    # Portanto, mitiga-se o erro de escala inerente ao ensaio de placa normatizado.
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
        # Logo, a rigidez do subleito é ponderada pelas dimensões reais da sapata.
        ks_real = ks_nominal * ((B + 0.305) / (2 * B)) ** 2
    elif soil["type"] == "coesivo":
        # Redução do coeficiente ks para considerar a influência da largura da base em solos argilosos.
        # Sendo assim, previnem-se recalques excessivos por adensamento lateral.
        ks_real = ks_nominal * (0.305 / B)
    else:
        ks_real = ks_nominal

    # Cálculo da rigidez equivalente da mola de apoio vertical (K_z) para simulação da base elástica.
    K_z = (ks_real * B * L_footing) * 1000

    # Definição do engastamento elástico rotacional para modelagem precisa da interação solo-estrutura.
    I_x = (L_footing * B**3) / 12
    I_z = (B * L_footing**3) / 12
    K_theta_x = (ks_real * I_x) * 1000
    K_theta_z = (ks_real * I_z) * 1000

    if params.raw_truss:
        # Mapeamento topológico de nós e incidências para geometrias definidas via interface gráfica.
        for nid, node in params.raw_truss.nodes.items():
            nodes_coords[nid] = (node.x, node.y, node.z)
            model.add_node(nid, node.x, node.y, node.z)

            if node.support != "None":
                if node.support in ["Pinned", "Roller"]:
                    # Implementação das condições de contorno via molas de Winkler para simulação do apoio elástico.
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

            # Filtro de segurança: ignorar barras com comprimento nulo (colapso de nós) para evitar erros no solver.
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
        # Geração algorítmica da topologia paramétrica para modelos de treliça tipo Howe.
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

            # Validação geométrica para assegurar que a barra possua rigidez axial calculável.
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

        # Configuração das condições de fronteira elástica nos nós extremos da estrutura.
        base_nodes = ["FL0", "BL0", f"FL{n}", f"BL{n}"]
        for bn in base_nodes:
            model.def_support(bn, True, False, True, False, True, False)
            model.def_support_spring(bn, "DY", K_z)
            model.def_support_spring(bn, "RX", K_theta_x)
            model.def_support_spring(bn, "RZ", K_theta_z)

    # Distribuição das solicitações externas nos nós do banzo superior conforme área de influência nodal.
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

    # Superposição de efeitos entre carga permanente (peso próprio) e sobrecarga externa.
    # Portanto, a análise elástica linear reflete a condição de carregamento mais desfavorável.
    model.add_load_combo("LC1", {"External": 1.0, "Dead": 1.0})

    try:
        model.analyze(check_statics=True, log=False)
    except Exception as e:
        return [], {}, {"_ERROR_": str(e)}, 0.0

    member_results = []
    max_u_per_group = {}
    for m in members_to_analyze:
        mid = f"M{m['id']}"
        # Extração dos esforços envoltórios axiais para verificação do estado limite último.
        f_max = model.members[mid].max_axial("LC1")
        f_min = model.members[mid].min_axial("LC1")

        if (
            math.isnan(f_max)
            or math.isinf(f_max)
            or math.isnan(f_min)
            or math.isinf(f_min)
        ):
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
