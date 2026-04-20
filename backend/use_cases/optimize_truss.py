import pandas as pd
import os
import asyncio
import time
import multiprocessing
import psutil
from concurrent.futures import ProcessPoolExecutor
from fastapi import Request
from domain.models import TrussRequest, OptimizationResponse
from infrastructure.fea.pynite_solver import build_and_solve_truss


def load_materials():
    """
    Carrega propriedades mecânicas e custos estruturais via CSV.
    Trade-off: I/O síncrono no startup. O cache em memória mitiga gargalos durante as iterações do solver.
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
    Carrega catálogo discreto de seções transversais comerciais.
    """
    csv_path = os.path.join(
        os.path.dirname(__file__), "..", "infrastructure", "data", "profiles.csv"
    )
    df = pd.read_csv(csv_path)
    return df.to_dict("records")


def optimize_for_material_worker(
    params_dict: dict, profiles: list, material: dict, groups: list, queue
) -> dict:
    """
    Offload da busca heurística para um worker isolado via multiprocessing.
    Justificativa: O solver FEA é CPU-bound. Executar na thread principal bloquearia o event loop do FastAPI.
    Trade-off: Aumenta o footprint de memória devido ao IPC (Pickling), mas garante estabilidade na API sob concorrência.
    """
    # Importação local para o worker multiprocessado.
    from infrastructure.fea.pynite_solver import build_and_solve_truss
    from domain.models import TrussRequest

    # Reconstrução do pydantic model a partir do dict (Pickle limitation do multiprocessing).
    params = TrussRequest(**params_dict)

    num_profiles = len(profiles)
    max_iter = 30
    current_profile_indices = {g: 0 for g in groups}
    iteration = 0
    worker_id = material["name"]
    valid_for_material = False
    last_valid_result = None
    last_error_msg = "A resistência máxima dos materiais foi atingida."
    upgrade_history = ""

    queue.put(
        {
            "worker_id": worker_id,
            "message": "Preparando o modelo estrutural...",
        }
    )

    while iteration < max_iter:
        iteration += 1

        # Pipeline de formatação de progresso para monitoramento via IPC.
        current_profiles_str = ", ".join(
            [
                f"{g}: {profiles[idx]['Name']}"
                for g, idx in current_profile_indices.items()
                if g != "Padrão"
            ]
        )
        if not current_profiles_str:
            current_profiles_str = (
                f"Perfil: {profiles[current_profile_indices.get('Padrão', 0)]['Name']}"
            )

        status_msg = f"Passo {iteration}/{max_iter} | Perfis: {current_profiles_str}"
        if upgrade_history:
            status_msg += f" | Status: {upgrade_history}"

        queue.put({"worker_id": worker_id, "message": status_msg})

        members, nodes, max_u_per_group, total_weight = build_and_solve_truss(
            params, current_profile_indices, profiles, material
        )

        if "_ERROR_" in max_u_per_group:
            last_error_msg = f"Identificamos que a estrutura não suporta as cargas aplicadas. Recomendamos rever o formato ou os apoios."
            queue.put({"worker_id": worker_id, "message": last_error_msg})
            break

        all_ok = True
        upgraded_any = False
        upgrade_msgs = []

        for g, u in max_u_per_group.items():
            if g == "_ERROR_":
                continue
            if u > 1.0:
                all_ok = False
                old_profile = profiles[current_profile_indices[g]]["Name"]
                if current_profile_indices.get(g, 0) < num_profiles - 1:
                    current_profile_indices[g] += 1
                    new_profile = profiles[current_profile_indices[g]]["Name"]
                    upgraded_any = True
                    upgrade_msgs.append(
                        f"{old_profile} em {g} esgotou a capacidade (U={u:.2f})"
                    )
                else:
                    all_ok = False
                    last_error_msg = f"Identificamos que o peso aplicado exige materiais além do limite comercial disponível para o grupo {g}. Recomendamos reduzir a carga."
                    queue.put({"worker_id": worker_id, "message": last_error_msg})
                    break

            # Hit da solução ótima (local) para o material específico.
            valid_for_material = True
            total_cost = total_weight * material["cost_kg"]
            last_valid_result = {
                "weight": total_weight,
                "cost": total_cost,
                "material_name": material["name"],
                "members": members,
                "nodes": nodes,
            }
            queue.put(
                {
                    "worker_id": worker_id,
                    "message": f"Cálculo finalizado. Custo estimado: R$ {total_cost:.2f}",
                }
            )
            break

        if not upgraded_any:
            break

        upgrade_history = ", ".join(upgrade_msgs)

    if valid_for_material:
        return {"success": True, "result": last_valid_result}
    else:
        return {"success": False, "error": last_error_msg, "material_name": worker_id}


async def optimize_truss_use_case(
    params: TrussRequest, request: Request = None, progress_callback=None
) -> OptimizationResponse:
    """
    Coordena a execução concorrente do solver para múltiplos materiais.
    Mapeia workers aos cores físicos disponíveis via ProcessPoolExecutor.
    """
    manager = None
    executor = None
    try:
        start_time = time.time()

        # Carregamento dos dados.
        profiles = load_profiles()
        materials_catalog = load_materials()
        num_materials = len(materials_catalog)

        if params.raw_truss:
            groups = list(set(m.group for m in params.raw_truss.members if m.group))
            if not groups:
                groups = ["Padrão"]
        else:
            groups = [
                "Banzo Superior",
                "Banzo Inferior",
                "Montante",
                "Diagonal",
                "Transversal",
                "Contraventamento",
            ]

        # Inicializa Manager para orquestração de estado IPC e Pool de Processos.
        manager = multiprocessing.Manager()
        queue = manager.Queue()
        executor = ProcessPoolExecutor(max_workers=os.cpu_count())

        futures = []
        current_logs = {
            mat["name"]: "Aguardando processamento..." for mat in materials_catalog
        }

        # Serialização para dict para evitar overhead e falhas no pickling via ProcessPoolExecutor.
        params_dict = params.dict()

        # Execução em paralelo.
        for material in materials_catalog:
            future = executor.submit(
                optimize_for_material_worker,
                params_dict,
                profiles,
                material,
                groups,
                queue,
            )
            futures.append(future)

        materials_completed = 0
        while materials_completed < num_materials:
            # Prevenção ativa de OOM (Out Of Memory). Graceful shutdown caso a memória atinja 90%.
            memory_usage = psutil.virtual_memory().percent
            if memory_usage > 90:
                if executor:
                    executor.shutdown(wait=False, cancel_futures=True)
                if manager:
                    manager.shutdown()
                return OptimizationResponse(
                    is_structurally_stable=False,
                    status_message=f"Processamento interrompido: O modelo excedeu o limite de memória do servidor. Tente reduzir as dimensões.",
                    total_weight=0,
                    members=[],
                    nodes={},
                )

            # Anti-hanging: Interrompe workers se a conexão WebSocket/HTTP for encerrada.
            if request and await request.is_disconnected():
                raise asyncio.CancelledError("Desconexão do cliente.")

            # Drainer da Queue IPC não bloqueante.
            while not queue.empty():
                try:
                    msg = queue.get_nowait()
                    current_logs[msg["worker_id"]] = msg["message"]
                except:
                    break

            # Cálculo do progresso.
            done_count = sum(1 for f in futures if f.done())
            if done_count > materials_completed:
                materials_completed = done_count

            if progress_callback:
                await progress_callback(
                    main_progress=(materials_completed / num_materials) * 100,
                    current_logs=current_logs,
                )

            if materials_completed < num_materials:
                await asyncio.sleep(0.5)

        # Seleção da solução mais econômica.
        best_overall = None
        min_cost = float("inf")
        last_error = "Não foi possível encontrar uma solução válida."

        for future in futures:
            res = future.result()
            if res["success"]:
                if res["result"]["cost"] < min_cost:
                    min_cost = res["result"]["cost"]
                    best_overall = res["result"]
            else:
                last_error = res["error"]

        if best_overall:
            return OptimizationResponse(
                is_structurally_stable=True,
                status_message=f"Análise finalizada. O material {best_overall['material_name']} é a opção mais econômica.",
                total_weight=best_overall["weight"],
                total_cost=best_overall["cost"],
                winning_material=best_overall["material_name"],
                members=best_overall["members"],
                nodes=best_overall["nodes"],
            )

        return OptimizationResponse(
            is_structurally_stable=False,
            status_message=last_error,
            total_weight=0,
            members=[],
            nodes={},
        )

    except asyncio.CancelledError:
        # Kill dos child processes para evitar workers zombies em caso de disconnect.
        if executor:
            executor.shutdown(wait=False, cancel_futures=True)
        if manager:
            manager.shutdown()
        raise
    except Exception as e:
        if executor:
            executor.shutdown(wait=False, cancel_futures=True)
        if manager:
            manager.shutdown()
        return OptimizationResponse(
            is_structurally_stable=False,
            status_message=f"Erro interno na análise: {str(e)}",
            total_weight=0,
            members=[],
            nodes={},
        )
    finally:
        # Cleanup garantido do pool e recursos IPC.
        if executor:
            executor.shutdown(wait=True)
        if manager:
            manager.shutdown()
