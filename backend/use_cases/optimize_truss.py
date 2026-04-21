import pandas as pd
import os
import asyncio
import time
import multiprocessing
import psutil
import signal
from concurrent.futures import ProcessPoolExecutor
from fastapi import Request
from domain.models import TrussRequest, OptimizationResponse


def load_materials():
    """
    Carrega propriedades mecânicas e custos estruturais via CSV.
    I/O síncrono no startup. O cache em memória mitiga gargalos durante as iterações do solver.
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
    params_dict: dict, profiles: list, material: dict, groups: list, queue, cancel_event
) -> dict:
    """
    Offload da busca heurística para um worker isolado via multiprocessing.
    O solver FEA é CPU-bound. Executar na thread principal bloquearia o event loop do FastAPI.
    Aumenta o footprint de memória devido ao IPC (Pickling), mas garante estabilidade na API sob concorrência.
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

    queue.put({"worker_id": worker_id, "message": "Preparando o modelo estrutural..."})

    while iteration < max_iter:
        # Verificação atômica de cancelamento para evitar processamento inútil (Zombie Avoidance).
        if cancel_event.is_set():
            return {
                "success": False,
                "error": "Cancelado pelo sistema.",
                "material_name": worker_id,
            }

        iteration += 1
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

        all_ok = True
        upgraded_any = False
        upgrade_msgs = []
        exhausted_catalogue = False

        if "_ERROR_" in max_u_per_group:
            # Erros numéricos (divergência/singularidade) costumam ser resolvidos com maior rigidez.
            # Forçamos o upgrade de todos os grupos para tentar estabilizar a matriz na próxima iteração.
            all_ok = False
            for g in current_profile_indices:
                if current_profile_indices[g] < num_profiles - 1:
                    current_profile_indices[g] += 1
                    upgraded_any = True
                else:
                    exhausted_catalogue = True

            if not upgraded_any or exhausted_catalogue:
                last_error_msg = f"A estrutura apresentou instabilidade que impede o cálculo: {max_u_per_group['_ERROR_']}"
                queue.put({"worker_id": worker_id, "message": last_error_msg})
                break
            continue

        # Corrigida indentação e lógica de validação do algoritmo guloso.
        # Todos os grupos devem ser validados (U <= 1.0) antes de marcar como solução válida.
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
                    upgrade_msgs.append(f"{old_profile} em {g} (U={u:.2f})")
                else:
                    # Fuga completa do laço quando o catálogo se esgota (CPU Waste Prevention).
                    exhausted_catalogue = True
                    last_error_msg = f"Os materiais disponíveis não são suficientes para suportar a carga exigida no grupo {g}."
                    queue.put({"worker_id": worker_id, "message": last_error_msg})
                    break

        if exhausted_catalogue:
            break

        if all_ok:
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
                    "message": f"Cálculo concluído. Custo estimado: R$ {total_cost:.2f}",
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
    """
    manager = None
    executor = None
    cancel_event = None
    try:
        profiles = load_profiles()
        materials_catalog = load_materials()
        num_materials = len(materials_catalog)

        if params.raw_truss:
            groups = list(
                set(m.group for m in params.raw_truss.members if m.group)
            ) or ["Padrão"]
        else:
            groups = [
                "Banzo Superior",
                "Banzo Inferior",
                "Montante",
                "Diagonal",
                "Transversal",
                "Contraventamento",
            ]

        manager = multiprocessing.Manager()
        queue = manager.Queue()
        # Evento para sinalização atômica de cancelamento entre processos.
        cancel_event = manager.Event()
        executor = ProcessPoolExecutor(max_workers=os.cpu_count())

        futures = []
        current_logs = {mat["name"]: "Aguardando..." for mat in materials_catalog}
        params_dict = params.dict()

        for material in materials_catalog:
            futures.append(
                executor.submit(
                    optimize_for_material_worker,
                    params_dict,
                    profiles,
                    material,
                    groups,
                    queue,
                    cancel_event,
                )
            )

        materials_completed = 0
        while materials_completed < num_materials:
            if psutil.virtual_memory().percent > 90:
                cancel_event.set()
                break

            if request and await request.is_disconnected():
                cancel_event.set()
                raise asyncio.CancelledError("Desconexão do cliente.")

            while not queue.empty():
                try:
                    msg = queue.get_nowait()
                    current_logs[msg["worker_id"]] = msg["message"]
                except:
                    break

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

        best_overall = None
        min_cost = float("inf")
        last_error = "Não foi possível encontrar uma solução válida com os materiais disponíveis."

        for future in futures:
            try:
                res = future.result()
                if res["success"]:
                    if res["result"]["cost"] < min_cost:
                        min_cost = res["result"]["cost"]
                        best_overall = res["result"]
                else:
                    last_error = res["error"]
            except Exception as e:
                last_error = f"Ocorreu um erro interno no servidor: {str(e)}"

        if best_overall:
            return OptimizationResponse(
                is_structurally_stable=True,
                status_message=f"A análise foi concluída com sucesso. O material otimizado para a estrutura é: {best_overall['material_name']}.",
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
        if cancel_event:
            cancel_event.set()
        raise
    except Exception as e:
        if cancel_event:
            cancel_event.set()
        return OptimizationResponse(
            is_structurally_stable=False,
            status_message=f"Ocorreu um erro interno durante a análise estrutural: {str(e)}",
            total_weight=0,
            members=[],
            nodes={},
        )
    finally:
        # Hard Kill de processos filhos para evitar zumbis DoS após shutdown.
        if executor:
            for pid in list(executor._processes.keys()):
                try:
                    os.kill(pid, signal.SIGKILL)
                except:
                    pass
            executor.shutdown(wait=False, cancel_futures=True)
        if manager:
            manager.shutdown()
