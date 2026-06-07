"""
truss_solver_ce.py
==================
Solver FEA para treliças metálicas otimizado para o estado do Ceará.

Perfis e materiais são carregados de arquivos CSV externos:
  data/profiles.csv  — catálogo de seções comerciais (Ue, L, RHS)
  data/materials.csv — propriedades dos materiais estruturais

Referências normativas:
  NBR 8800  — Projeto de estruturas de aço
  NBR 6120  — Cargas para o cálculo de estruturas de edificações
  NBR 6123  — Forças devidas ao vento em edificações
  NBR 14762 — Dimensionamento de estruturas de aço constituídas por perfis formados a frio

Correções aplicadas (v2):
  [C1] Carregamento lazy dos catálogos CSV (evita falha na importação)
  [C2] max_x / min_x movidos para dentro do bloco correto (evita NameError)
  [C3] combos definido antes do try/except (evita NameError no pós-processamento)
  [C4] LC2 inclui carga External com fator 1.0 (NBR 8800 combinação com vento)
  [C5] Fator rho corrigido para kg/m³ sem escalonamento indevido
  [C6] profile_indices com validação de bounds (evita IndexError)
  [C7] Limite de deslocamento baseado em L/300 (NBR 8800) em vez de 1 m fixo
  [C8] commercial_bar_waste corrigido para peças longas (emenda em vez de descarte)
  [C9] Tabela S2 estendida até 30 m para coberturas industriais altas
  [C10] CP_SUCAO_BARLAVENTO parametrizado por inclinação de cobertura
"""

import csv
import math
import os

import numpy as np
from Pynite import FEModel3D

from domain.models import MemberResult, NodeResult, TrussRequest

# ==============================================================================
# CAMINHOS DOS CATÁLOGOS
# ==============================================================================

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_HERE, "..", "infrastructure", "fea")

PROFILES_CSV  = os.path.join(_DATA_DIR, "profiles.csv")
MATERIALS_CSV = os.path.join(_DATA_DIR, "materials.csv")

# ==============================================================================
# LEITURA DOS CATÁLOGOS CSV — [C1] Carregamento lazy
# ==============================================================================

# Variáveis internas; acesse sempre via get_profiles_catalog() / get_materials_catalog()
_PROFILES_CATALOG: list[dict] | None = None
_MATERIALS_CATALOG: dict[str, dict] | None = None


def _load_profiles(path: str = PROFILES_CSV) -> list[dict]:
    """
    Lê data/profiles.csv e retorna lista de dicionários prontos para o modelo FEA.

    Colunas obrigatórias: Name, Area_m2, Ix_m4, Iy_m4, J_m4
    Colunas opcionais:    Familia, Uso_recomendado (usadas apenas para filtragem/relatório)
    Linhas iniciadas com '#' são ignoradas (comentários de cabeçalho).
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Catálogo de perfis não encontrado: {path}\n"
            f"Certifique-se de que 'profiles.csv' está em '{_DATA_DIR}'."
        )
    profiles = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(row for row in f if not row.startswith("#"))
        for row in reader:
            profiles.append(
                {
                    "Name":    row["Name"].strip(),
                    "Familia": row.get("Familia", "").strip(),
                    "Uso":     row.get("Uso_recomendado", "").strip(),
                    "Area":    float(row["Area_m2"]),
                    "Ix":      float(row["Ix_m4"]),
                    "Iy":      float(row["Iy_m4"]),
                    "J":       float(row["J_m4"]),
                }
            )
    if not profiles:
        raise ValueError(f"Catálogo de perfis vazio: {path}")
    return profiles


def _load_materials(path: str = MATERIALS_CSV) -> dict[str, dict]:
    """
    Lê data/materials.csv e retorna dicionário indexado pelo campo 'name'.

    Campos retornados (unidades internas do solver):
      E   → GPa   (float)
      G   → GPa   (float)
      nu  → adimensional
      fy  → MPa   (float)
      fu  → MPa   (float)
      rho → kg/m³ (float)

    Linhas iniciadas com '#' são ignoradas.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Catálogo de materiais não encontrado: {path}\n"
            f"Certifique-se de que 'materials.csv' está em '{_DATA_DIR}'."
        )
    materials = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(row for row in f if not row.startswith("#"))
        for row in reader:
            name = row["name"].strip()
            materials[name] = {
                "name": name,
                "E":    float(row["E_GPa"]),
                "G":    float(row["G_GPa"]),
                "nu":   float(row["nu"]),
                "fy":   float(row["fy_MPa"]),
                "fu":   float(row["fu_MPa"]),
                "rho":  float(row["rho_kg_m3"]),
            }
    if not materials:
        raise ValueError(f"Catálogo de materiais vazio: {path}")
    return materials


# [C1] Funções de acesso lazy — os CSVs só são lidos na primeira chamada
def get_profiles_catalog() -> list[dict]:
    """Retorna o catálogo de perfis, carregando do CSV se necessário."""
    global _PROFILES_CATALOG
    if _PROFILES_CATALOG is None:
        _PROFILES_CATALOG = _load_profiles()
    return _PROFILES_CATALOG


def get_materials_catalog() -> dict[str, dict]:
    """Retorna o catálogo de materiais, carregando do CSV se necessário."""
    global _MATERIALS_CATALOG
    if _MATERIALS_CATALOG is None:
        _MATERIALS_CATALOG = _load_materials()
    return _MATERIALS_CATALOG


def get_material(name: str) -> dict:
    """Retorna material pelo nome; lança KeyError descritivo se não encontrado."""
    catalog = get_materials_catalog()
    if name not in catalog:
        available = ", ".join(catalog.keys())
        raise KeyError(f"Material '{name}' não encontrado. Disponíveis: {available}")
    return catalog[name]


def get_profiles_by_family(family: str) -> list[dict]:
    """Filtra perfis pelo campo Familia (ex.: 'Ue', 'L', 'RHS')."""
    return [p for p in get_profiles_catalog() if p["Familia"] == family]


# ==============================================================================
# BANCO DE DADOS DE SOLOS — Winkler-Terzaghi
# ==============================================================================

SOIL_DATABASE = {
    "Areia Fofa":     {"ks1": 15000,  "type": "granular"},
    "Areia Compacta": {"ks1": 100000, "type": "granular"},
    "Argila Mole":    {"ks1": 10000,  "type": "coesivo"},
    "Argila Rija":    {"ks1": 40000,  "type": "coesivo"},
    "Rocha":          {"ks1": 250000, "type": "rigid"},
}

# ==============================================================================
# PARÂMETROS CLIMÁTICOS REGIONAIS — CEARÁ
# NBR 6123 e NBR 6120
# ==============================================================================

# Velocidade básica do vento V₀ por região [m/s] — NBR 6123, Figura 1
WIND_V0_CE = {
    "Litoral":  35.0,   # Fortaleza, Caucaia, Aquiraz, Cascavel …
    "Interior": 30.0,   # Sobral, Juazeiro do Norte, Quixadá …
}

# Fatores S1 e S3 (NBR 6123 §5.2 e §5.4)
S1 = 1.0   # Terreno plano — conservador para galpões industriais
S3 = 1.0   # Grupo 2 — estruturas industriais correntes

# [C9] Fator S2: rugosidade categoria II, classe B — NBR 6123, Tab. 1
# Tabela estendida até 30 m para coberturas industriais altas
_S2_CAT_II_B = {10: 0.98, 15: 1.05, 20: 1.10, 25: 1.13, 30: 1.16}

# [C10] Coeficientes externos de pressão para cobertura — NBR 6123, Anexo A
# Indexado pelo ângulo de inclinação da cobertura (graus)
# Sucção de barlavento: negativo (força para cima); valor em módulo
CP_SUCAO_POR_ANGULO = {
    0:  1.0,   # θ = 0°  (cobertura plana ou θ < 5°) — sucção máxima
    10: 0.9,
    20: 0.5,
    30: 0.0,   # θ ≥ 30° — pressão positiva; sem sucção de barlavento
}

def get_cp_sucao(roof_angle_deg: float = 0.0) -> float:
    """
    Interpola o Cp de sucção de barlavento pelo ângulo da cobertura [graus].
    Retorna valor em módulo (sempre ≥ 0).
    """
    angles = sorted(CP_SUCAO_POR_ANGULO)
    cps    = [CP_SUCAO_POR_ANGULO[a] for a in angles]
    if roof_angle_deg <= angles[0]:
        return cps[0]
    if roof_angle_deg >= angles[-1]:
        return cps[-1]
    for i in range(len(angles) - 1):
        if angles[i] <= roof_angle_deg <= angles[i + 1]:
            t = (roof_angle_deg - angles[i]) / (angles[i + 1] - angles[i])
            return cps[i] + t * (cps[i + 1] - cps[i])
    return cps[-1]


# Cargas de cobertura características gk [kN/m²] — NBR 6120, Tab. 3
COVER_LOADS = {
    "fibrocimento":      {"gk": 0.175, "descricao": "Telha fibrocimento 6 mm (~17,5 kg/m²)"},
    "metalica":          {"gk": 0.075, "descricao": "Telha metálica/sanduíche (~7,5 kg/m²)"},
    "ceramica_colonial": {"gk": 0.450, "descricao": "Telha colonial (~45 kg/m²) — evitar em galpões"},
}

# Sobrecarga de manutenção em cobertura inacessível [kN/m²] — NBR 6120, Tab. 1
QK_MANUTENCAO = 0.25

# Comprimento comercial de barra no Ceará [m]
COMMERCIAL_BAR_LENGTH = 6.0


# ==============================================================================
# FUNÇÕES AUXILIARES — VENTO E DESPERDÍCIO COMERCIAL
# ==============================================================================

def _compute_s2(height: float) -> float:
    """Interpola linearmente o fator S2 (Cat. II / Classe B) pela altura [m]."""
    heights = sorted(_S2_CAT_II_B)
    frs = [_S2_CAT_II_B[h] for h in heights]
    if height <= heights[0]:
        return frs[0]
    if height >= heights[-1]:
        return frs[-1]
    for i in range(len(heights) - 1):
        if heights[i] <= height <= heights[i + 1]:
            t = (height - heights[i]) / (heights[i + 1] - heights[i])
            return frs[i] + t * (frs[i + 1] - frs[i])
    return frs[-1]


def compute_wind_pressure(v0: float, height: float) -> float:
    """
    Pressão dinâmica de vento q [kN/m²] — NBR 6123 §5.1.

    q = 0,613 · Vk²  [N/m²]   →   Vk = V0 · S1 · S2 · S3
    """
    s2 = _compute_s2(height)
    vk = v0 * S1 * s2 * S3
    return 0.613 * vk**2 / 1000.0   # kN/m²


def commercial_bar_waste(length: float, bar_length: float = COMMERCIAL_BAR_LENGTH) -> float:
    """
    [C8] Percentual de retalho ao cortar uma barra comercial em peças de `length` metros.

    Para peças maiores que uma barra comercial, considera emenda (múltiplos inteiros
    de barras comerciais). Retorna valor em [0, 1]; 0 = desperdício zero.
    """
    if length <= 0:
        return 1.0
    if length > bar_length:
        # Peça longa: calcula quantas barras inteiras são necessárias e o retalho final
        bars_needed = math.ceil(length / bar_length)
        total_bought = bars_needed * bar_length
        return (total_bought - length) / total_bought
    cuts = math.floor(bar_length / length)
    return (bar_length - cuts * length) / bar_length


# ==============================================================================
# VERIFICAÇÃO ESTRUTURAL — NBR 8800
# ==============================================================================

def calculate_max_utilization(
    force, profile, length, material, group_name="Padrão", l_effective=None
):
    """
    Taxa de Utilização (U) conforme NBR 8800.
    Inclui coeficientes de minoração e limites de esbeltez normativa.
    """
    gamma_a1 = 1.10                          # NBR 8800 — minoração da resistência
    fy = (material["fy"] * 1e6) / gamma_a1   # [Pa]
    E  = material["E"] * 1e9                 # [Pa]
    A  = profile["Area"]

    I_min = min(profile["Ix"], profile["Iy"])
    r_min = math.sqrt(I_min / A)

    lk = l_effective if l_effective is not None else length
    slenderness = lk / r_min

    # Limites de esbeltez — NBR 8800, itens 5.2.8 e 5.3.4
    if force < -0.01 and slenderness > 200:
        return 999.0   # compressão
    if force >= -0.01 and slenderness > 300:
        return 999.0   # tração

    if force >= 0:
        capacity = A * fy
    else:
        ne      = (math.pi**2 * E * I_min) / (lk**2)
        lambda0 = math.sqrt((A * (material["fy"] * 1e6)) / ne)
        chi     = 0.658 ** (lambda0**2) if lambda0 <= 1.5 else 0.877 / (lambda0**2)
        capacity = chi * A * fy

    return abs(force) / capacity


def calculate_lk_map(members_to_analyze, params):
    """
    Mapeamento do Comprimento Efetivo (Lk) para banzos considerando travamentos reais.
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
        if m["group"] in ["Transversal", "Contraventamento"]:
            braced_nodes.add(m["node_start"])
            braced_nodes.add(m["node_end"])

    chord_graph = {}
    for m in members_to_analyze:
        if m["group"] in ["Banzo Superior", "Banzo Inferior"]:
            n1, n2 = m["node_start"], m["node_end"]
            chord_graph.setdefault(n1, []).append((n2, m["length"]))
            chord_graph.setdefault(n2, []).append((n1, m["length"]))

    lk_map = {}
    for m in members_to_analyze:
        if m["group"] in ["Banzo Superior", "Banzo Inferior"]:
            total_lk = m["length"]
            for start_node, other_node in [
                (m["node_start"], m["node_end"]),
                (m["node_end"], m["node_start"]),
            ]:
                curr, prev = start_node, other_node
                while curr not in braced_nodes:
                    neighbors = [c for c in chord_graph.get(curr, []) if c[0] != prev]
                    if not neighbors:
                        break
                    next_node, length = neighbors[0]
                    total_lk += length
                    prev, curr = curr, next_node
            lk_map[m["id"]] = total_lk
        else:
            lk_map[m["id"]] = m["length"]
    return lk_map


# ==============================================================================
# MONTAGEM E SOLUÇÃO FEA
# ==============================================================================

def build_and_solve_truss(
    params: TrussRequest,
    profile_indices: dict,
    profiles_catalog: list[dict] | None = None,
    material: dict | None = None,
    # ── Parâmetros climáticos regionais (CE) ─────────────────────────────────
    cover_type: str = "fibrocimento",
    wind_region: str = "Interior",
    roof_span: float | None = None,
    include_wind: bool = True,
    roof_angle_deg: float = 0.0,   # [C10] ângulo da cobertura em graus
):
    """
    Formulação FEA via Matriz de Rigidez Direta.

    Se `profiles_catalog` ou `material` forem None, os catálogos CSV são usados
    automaticamente (comportamento padrão recomendado).

    Combinações ELU aplicadas (NBR 8800 + NBR 6120 + NBR 6123):
      LC1 — Gravitação máxima : 1,4·Dead + 1,4·Cover + 1,4·Live + 1,4·External
      LC2 — Vento de sucção   : 1,0·External + 1,4·Dead + 1,4·Cover + 1,4·Wind
             (governa inversão de esforços — banzo inferior em compressão)
    """
    # ── Catálogos padrão (CSV) — [C1] lazy ───────────────────────────────────
    if profiles_catalog is None:
        profiles_catalog = get_profiles_catalog()
    if material is None:
        material = get_material("MR250")   # aço nacional mais comum no CE

    # ── Modelo FEA ────────────────────────────────────────────────────────────
    model = FEModel3D()
    nu = material["nu"]
    G  = material["G"] * 1e9   # Pa

    # [C5] rho em kg/m³ — sem fator de escala adicional (Pynite usa SI: kg, m, N)
    model.add_material(material["name"], material["E"] * 1e9, G, nu, material["rho"])

    for p in profiles_catalog:
        if p["Name"] not in model.sections:
            model.add_section(p["Name"], p["Area"], p["Ix"], p["Iy"], p["J"])

    nodes_coords: dict[str, tuple] = {}
    members_to_analyze: list[dict] = []

    # ── Fundação Winkler-Terzaghi ─────────────────────────────────────────────
    soil = SOIL_DATABASE.get(params.soil_type, SOIL_DATABASE["Rocha"])
    ks_nominal = (
        params.custom_ks
        if (params.soil_type == "Customizado" and params.custom_ks is not None)
        else soil["ks1"]
    )
    B         = max(params.footing_b, 0.305)
    L_footing = params.footing_l
    if soil["type"] == "granular":
        ks_real = ks_nominal * ((B + 0.305) / (2 * B)) ** 2
    elif soil["type"] == "coesivo":
        ks_real = ks_nominal * (0.305 / B)
    else:
        ks_real = ks_nominal
    K_z       = ks_real * B * L_footing * 1000
    K_theta_x = ks_real * (L_footing * B**3 / 12) * 1000
    K_theta_z = ks_real * (B * L_footing**3 / 12) * 1000

    # ── Helper interno ────────────────────────────────────────────────────────
    def add_member(m_id, n1, n2, group, length):
        p_idx   = profile_indices.get(group, profile_indices.get("Padrão", 0))
        # [C6] Validação de bounds para evitar IndexError
        p_idx   = max(0, min(p_idx, len(profiles_catalog) - 1))
        profile = profiles_catalog[p_idx]
        members_to_analyze.append(
            {
                "id":          m_id,
                "node_start":  n1,
                "node_end":    n2,
                "group":       group,
                "length":      length,
                "profile":     profile["Name"],
                "area":        profile["Area"],
                "unit_weight": profile["Area"] * material["rho"],
                "bar_waste":   commercial_bar_waste(length),   # [C8]
            }
        )
        mid = f"M{m_id}"
        model.add_member(mid, n1, n2, material["name"], profile["Name"])
        if group in ["Banzo Superior", "Banzo Inferior"]:
            model.def_releases(mid, Ryi=False, Rzi=False, Ryj=True, Rzj=True)
        else:
            model.def_releases(mid, Ryi=True, Rzi=True, Ryj=True, Rzj=True)

    # ── Geometria ─────────────────────────────────────────────────────────────
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
                    model.def_support(nid, False, False, True, False, True, False)
                    model.def_support_spring(nid, "DY", K_z)
                elif node.support == "Fixed":
                    model.def_support(nid, True, True, True, True, True, True)
        for m in params.raw_truss.members:
            n1c, n2c = nodes_coords[m.node_start], nodes_coords[m.node_end]
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(n1c, n2c)))
            if dist >= 0.001:
                add_member(m.id, m.node_start, m.node_end, m.group, dist)
    else:
        L, H, W, n = params.length, params.height, params.width, params.divisions
        dx = L / n
        for i in range(n + 1):
            x = i * dx
            for tag, y, z in [("FL", 0, 0), ("BL", 0, W), ("FU", H, 0), ("BU", H, W)]:
                model.add_node(f"{tag}{i}", x, y, z)
                nodes_coords[f"{tag}{i}"] = (x, y, z)
        for i in range(n):
            for s in ["F", "B"]:
                add_member(len(members_to_analyze), f"{s}L{i}", f"{s}L{i+1}", "Banzo Inferior", dx)
                add_member(len(members_to_analyze), f"{s}U{i}", f"{s}U{i+1}", "Banzo Superior", dx)
                add_member(len(members_to_analyze), f"{s}L{i}", f"{s}U{i}",   "Montante",       H)
                add_member(len(members_to_analyze), f"{s}L{i}", f"{s}U{i+1}", "Diagonal", math.sqrt(dx**2 + H**2))
            add_member(len(members_to_analyze), f"FL{i}", f"BL{i}", "Transversal", W)
            add_member(len(members_to_analyze), f"FU{i}", f"BU{i}", "Transversal", W)
            dxw = math.sqrt(dx**2 + W**2)
            for a, b in [(f"FL{i}", f"BL{i+1}"), (f"BL{i}", f"FL{i+1}"),
                         (f"FU{i}", f"BU{i+1}"), (f"BU{i}", f"FU{i+1}")]:
                add_member(len(members_to_analyze), a, b, "Contraventamento", dxw)
        add_member(len(members_to_analyze), f"FL{n}", f"BL{n}", "Transversal", W)
        add_member(len(members_to_analyze), f"FU{n}", f"BU{n}", "Transversal", W)
        for bn in ["FL0", "BL0", f"FL{n}", f"BL{n}"]:
            model.def_support(bn, True, False, True, False, True, False)
            model.def_support_spring(bn, "DY", K_z)
            model.def_support_spring(bn, "RX", K_theta_x)
            model.def_support_spring(bn, "RZ", K_theta_z)

    # ── Identificação de nós de carga ─────────────────────────────────────────
    is_bridge   = any("bridge" in (m["group"] or "").lower() for m in members_to_analyze)
    has_banzos  = any("banzo"  in (m["group"] or "").lower() for m in members_to_analyze)
    trib_width  = roof_span if roof_span else getattr(params, "width", 5.0)
    total_force_n = params.total_load * 9.81

    if is_bridge:
        target_nodes = [nd for nd, c in nodes_coords.items() if c[1] < 0.05]
    else:
        max_y = max(c[1] for c in nodes_coords.values())
        target_nodes = [nd for nd, c in nodes_coords.items() if c[1] >= max_y - 0.05]

    node_weights: dict[str, float] = {}
    total_influence = 0.0

    # [C2] min_x / max_x definidos antes do uso em span_x
    min_x = 0.0
    max_x = 0.0

    if target_nodes:
        min_x = min(nodes_coords[nd][0] for nd in target_nodes)
        max_x = max(nodes_coords[nd][0] for nd in target_nodes)
        for nd in target_nodes:
            x = nodes_coords[nd][0]
            w = 0.5 if has_banzos and (abs(x - min_x) < 0.01 or abs(x - max_x) < 0.01) else 1.0
            node_weights[nd] = w
            total_influence += w

        # Carga operacional (External)
        load_unit = total_force_n / total_influence
        for nd, w in node_weights.items():
            model.add_node_load(nd, "FY", -load_unit * w, case="External")

    # ── Peso próprio (Dead) ───────────────────────────────────────────────────
    node_dead = {nd: 0.0 for nd in nodes_coords}
    total_weight = 0.0
    for m in members_to_analyze:
        wt = m["unit_weight"] * m["length"]
        total_weight += wt
        node_dead[m["node_start"]] += wt / 2
        node_dead[m["node_end"]]   += wt / 2
    for nd, wt in node_dead.items():
        model.add_node_load(nd, "FY", -wt * 9.81, case="Dead")

    # [C2] span_x calculado com min_x / max_x sempre definidos
    span_x = (max_x - min_x) if (target_nodes and max_x > min_x) else 1.0

    # ── Carga permanente de cobertura (Cover) — NBR 6120 ─────────────────────
    if target_nodes and not is_bridge:
        gk = COVER_LOADS.get(cover_type, COVER_LOADS["fibrocimento"])["gk"]
        cover_unit_n = (gk * span_x * trib_width * 1000) / total_influence
        for nd, w in node_weights.items():
            model.add_node_load(nd, "FY", -cover_unit_n * w, case="Cover")

        # ── Sobrecarga de manutenção (Live) — NBR 6120 ───────────────────────
        live_unit_n = (QK_MANUTENCAO * span_x * trib_width * 1000) / total_influence
        for nd, w in node_weights.items():
            model.add_node_load(nd, "FY", -live_unit_n * w, case="Live")

    # ── Vento de sucção (Wind) — NBR 6123 ────────────────────────────────────
    # Sucção → força para CIMA (FY positivo); inverte esforços → verificar flambagem
    if include_wind and target_nodes and not is_bridge:
        max_h = max(c[1] for c in nodes_coords.values())
        v0    = WIND_V0_CE.get(wind_region, WIND_V0_CE["Interior"])
        q     = compute_wind_pressure(v0, max_h)             # kN/m²
        cp    = get_cp_sucao(roof_angle_deg)                  # [C10]
        wind_unit_n = (q * cp * span_x * trib_width * 1000) / total_influence
        for nd, w in node_weights.items():
            model.add_node_load(nd, "FY", +wind_unit_n * w, case="Wind")

    # ── Combinações ELU — NBR 8800 §7 ────────────────────────────────────────
    model.add_load_combo("LC1", {"External": 1.4, "Dead": 1.4, "Cover": 1.4, "Live": 1.4})
    if include_wind:
        # [C4] LC2 inclui External com fator 1.0 (carga permanente na combinação de vento)
        model.add_load_combo("LC2", {"External": 1.0, "Dead": 1.4, "Cover": 1.4, "Wind": 1.4})

    # [C3] combos definido ANTES do try/except para garantir acesso no pós-processamento
    combos = ["LC1", "LC2"] if include_wind else ["LC1"]

    # ── [C7] Limite de deslocamento baseado em L/300 — NBR 8800 ──────────────
    span_ref  = getattr(params, "length", 1.0) or 1.0
    desl_lim  = span_ref / 300.0

    # ── Análise ───────────────────────────────────────────────────────────────
    try:
        model.analyze(check_statics=True, log=False)
        for nid_chk, node_chk in model.nodes.items():
            if hasattr(node_chk, "DY") and isinstance(node_chk.DY, dict):
                for combo in combos:
                    dy = node_chk.DY.get(combo, 0)
                    if abs(dy) > desl_lim:
                        return (
                            [], {}, 
                            {"_ERROR_": (
                                f"Deslocamento excessivo no nó {nid_chk} ({combo}): "
                                f"{abs(dy)*1000:.1f} mm > L/300 = {desl_lim*1000:.1f} mm."
                            )},
                            0.0,
                        )
    except Exception as exc:
        return [], {}, {"_ERROR_": str(exc)}, 0.0

    # ── Pós-processamento ─────────────────────────────────────────────────────
    lk_map = calculate_lk_map(members_to_analyze, params)
    member_results = []
    max_u_per_group: dict[str, float] = {}

    for m in members_to_analyze:
        mid = f"M{m['id']}"
        axial_f = 0.0
        for combo in combos:
            try:
                for f in [model.members[mid].max_axial(combo), model.members[mid].min_axial(combo)]:
                    if not (math.isnan(f) or math.isinf(f)) and abs(f) > abs(axial_f):
                        axial_f = f
            except Exception:
                pass

        if math.isnan(axial_f) or math.isinf(axial_f):
            return ([], {}, {"_ERROR_": "Divergência numérica na análise."}, 0.0)

        p_idx   = profile_indices.get(m["group"], profile_indices.get("Padrão", 0))
        p_idx   = max(0, min(p_idx, len(profiles_catalog) - 1))   # [C6]
        profile = profiles_catalog[p_idx]
        u = calculate_max_utilization(axial_f, profile, m["length"], material, m["group"], lk_map[m["id"]])
        if m["group"] not in max_u_per_group or u > max_u_per_group[m["group"]]:
            max_u_per_group[m["group"]] = u

        member_results.append(
            MemberResult(
                id=m["id"],
                node_start=m["node_start"],
                node_end=m["node_end"],
                group=m["group"],
                profile=profile["Name"],
                axial_force=float(axial_f),
                utilization=float(u),
                stress_type="Tração" if axial_f > 0 else "Compressão",
                bar_waste=float(m["bar_waste"]),
            )
        )

    nodes_results = {}
    for nid, c in nodes_coords.items():
        sup = (
            params.raw_truss.nodes[nid].support
            if (params.raw_truss and nid in params.raw_truss.nodes)
            else "None"
        )
        nodes_results[nid] = NodeResult(id=nid, x=c[0], y=c[1], z=c[2], support=sup)

    return member_results, nodes_results, max_u_per_group, total_weight
