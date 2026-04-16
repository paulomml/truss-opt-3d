import pandas as pd
import os
from domain.models import TrussRequest, OptimizationResponse
from infrastructure.fea.pynite_solver import build_and_solve_truss


def load_materials():
    """
    Importação das propriedades mecânicas e metalúrgicas dos materiais estruturais.
    Os valores de tensão de escoamento (fy) e ruptura (fu) fundamentam a verificação dos estados limites normativos.
    """
    csv_path = os.path.join(
        os.path.dirname(__file__), "..", "infrastructure", "data", "materials.csv"
    )
    df = pd.read_csv(csv_path)
    materials = []
    for _, row in df.iterrows():
        materials.append(
            {
                "name": row["Material"],
                "fy": row["fy_MPa"],
                "fu": row["fu_MPa"],
                "E": row["E_GPa"],
                "rho": row["density_kgm3"],
                "cost_kg": row["cost_BRL_kg"],
            }
        )
    return materials


def load_profiles():
    """
    Carregamento do banco de dados discreto de seções transversais comerciais.
    Sendo assim, o sistema pode iterar sobre perfis tubulares reais para encontrar a seção que minimiza o peso próprio.
    """
    csv_path = os.path.join(
        os.path.dirname(__file__), "..", "infrastructure", "data", "profiles.csv"
    )
    df = pd.read_csv(csv_path)
    return df.to_dict("records")


def optimize_truss_use_case(params: TrussRequest) -> OptimizationResponse:
    """
    Implementação da rotina de otimização de custo global via busca exaustiva no espaço de soluções discretas.
    O solver busca minimizar a função objetivo de custo, garantindo que a taxa de utilização (U) não exceda a unidade.
    """
    try:
        profiles = load_profiles()
        num_profiles = len(profiles)
        materials_catalog = load_materials()

        if params.raw_truss:
            groups = list(set(m.group for m in params.raw_truss.members if m.group))
            if not groups:
                groups = ["Default"]
        else:
            groups = [
                "Top Chord",
                "Bottom Chord",
                "Vertical",
                "Diagonal",
                "Transverse",
                "X-Bracing",
            ]

        best_overall_response = None
        min_total_cost = float("inf")

        last_error_msg = "Nenhuma combinação de material e perfil atende aos requisitos de projeto estrutural."

        # Varredura sistemática do catálogo de materiais para identificação da liga com melhor desempenho econômico.
        for material in materials_catalog:
            current_profile_indices = {g: 0 for g in groups}
            iteration = 0
            max_iterations = 30

            valid_for_material = False
            last_valid_result = None

            # Algoritmo de busca local para definição das seções transversais mínimas necessárias por grupo de barras.
            while iteration < max_iterations:
                iteration += 1

                # Resolução do equilíbrio estático considerando o acoplamento solo-estrutura.
                # Portanto, as deformações do apoio elástico influenciam a redistribuição dos esforços internos.
                members, nodes, max_u_per_group, total_weight = build_and_solve_truss(
                    params, current_profile_indices, profiles, material
                )

                if "_ERROR_" in max_u_per_group:
                    last_error_msg = f"Instabilidade ou erro na análise matricial: {max_u_per_group['_ERROR_']}"
                    break

                all_ok = True
                upgraded_any = False

                for g, u in max_u_per_group.items():
                    if g == "_ERROR_":
                        continue
                    if u > 1.0:
                        all_ok = False
                        # Atualização da rigidez do membro através do incremento da área da seção transversal.
                        # Logo, busca-se reduzir a taxa de utilização para valores inferiores ao limite de escoamento ou flambagem.
                        if current_profile_indices.get(g, 0) < num_profiles - 1:
                            current_profile_indices[g] = (
                                current_profile_indices.get(g, 0) + 1
                            )
                            upgraded_any = True
                        else:
                            all_ok = False
                            last_error_msg = f"A solicitação axial excedeu a capacidade máxima do perfil {profiles[current_profile_indices.get(g, 0)]['Name']}."
                            break

                if all_ok:
                    valid_for_material = True
                    # Determinação da viabilidade financeira a partir da cubagem de material e cotação de mercado.
                    total_cost = total_weight * material["cost_kg"]
                    last_valid_result = {
                        "weight": total_weight,
                        "cost": total_cost,
                        "material_name": material["name"],
                        "members": members,
                        "nodes": nodes,
                    }
                    break

                if not upgraded_any:
                    break

            # Atualização do estado global da solução ótima baseada no critério de eficiência econômica.
            if valid_for_material and last_valid_result["cost"] < min_total_cost:
                min_total_cost = last_valid_result["cost"]
                best_overall_response = OptimizationResponse(
                    is_structurally_stable=True,
                    status_message=f"Otimização concluída: Material {material['name']} selecionado pelo menor custo global.",
                    total_weight=last_valid_result["weight"],
                    total_cost=last_valid_result["cost"],
                    winning_material=last_valid_result["material_name"],
                    members=last_valid_result["members"],
                    nodes=last_valid_result["nodes"],
                )

        if best_overall_response:
            return best_overall_response

        return OptimizationResponse(
            is_structurally_stable=False,
            status_message=f"Erro: {last_error_msg}",
            total_weight=0,
            members=[],
            nodes={},
        )

    except Exception as e:
        return OptimizationResponse(
            is_structurally_stable=False,
            status_message=f"Erro no processamento da rotina de otimização: {str(e)}",
            total_weight=0,
            members=[],
            nodes={},
        )
