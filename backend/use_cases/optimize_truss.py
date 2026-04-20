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


def optimize_for_material_worker(
    params_dict: dict, profiles: list, material: dict, groups: list, queue
) -> dict:
    """
    Worker isolado para processamento via Multiprocessing.
    Esta função executa a busca exaustiva de perfis para um material específico.
    Sendo assim, o uso de CPU é maximizado sem interferir no event loop principal.
    """
    # Importação local necessária para o worker multiprocessado.
    from infrastructure.fea.pynite_solver import build_and_solve_truss
    from domain.models import TrussRequest

    # Reconstrução do objeto de parâmetros dentro do processo filho.
    params = TrussRequest(**params_dict)

    num_profiles = len(profiles)
    max_iter = 30
    current_profile_indices = {g: 0 for g in groups}
    # Inicialização das variáveis de controle de iteração e persistência de dados.
    iteration = 0
    worker_id = material["name"]
    valid_for_material = False
    last_valid_result = None
    # Mensagens de status e erro refinadas para melhor compreensão técnica pelo usuário final.
    last_error_msg = "A resistência máxima dos materiais disponíveis foi atingida."
    upgrade_history = ""

    queue.put(
        {
            "worker_id": worker_id,
            "message": "Iniciando a preparação do modelo estrutural...",
        }
    )

    while iteration < max_iter:
        iteration += 1

        # Formata os perfis atuais para exibição detalhada.
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

        # Envio de progresso granular via Queue para o processo pai (IPC).
        # Logo, o usuário percebe exatamente quais perfis estão em teste e o motivo das trocas.
        queue.put({"worker_id": worker_id, "message": status_msg})

        # Resolução do sistema linear e cálculo da matriz de rigidez global.
        members, nodes, max_u_per_group, total_weight = build_and_solve_truss(
            params, current_profile_indices, profiles, material
        )

        if "_ERROR_" in max_u_per_group:
            last_error_msg = f"Falha de estabilidade: A estrutura não é capaz de suportar as cargas aplicadas."
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
                        f"{old_profile} em {g} excedeu limite (U={u:.2f})"
                    )
                else:
                    all_ok = False
                    last_error_msg = f"Dimensionamento inviável: O perfil de maior resistência ({old_profile}) foi insuficiente para o grupo {g}."
                    queue.put({"worker_id": worker_id, "message": last_error_msg})
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
                    "message": f"Processamento finalizado para este material. Custo estimado: R$ {total_cost:.2f}",
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
    Orquestrador da otimização estrutural utilizando um pool de processos.
    Logo, a carga computacional é distribuída por todos os núcleos disponíveis da CPU.
    """
    manager = None
    executor = None
    try:
        start_time = time.time()

        # Carregamento preliminar dos dados para partilha com os workers.
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

        # Inicialização do mecanismo IPC e do pool de processos.
        manager = multiprocessing.Manager()
        queue = manager.Queue()
        executor = ProcessPoolExecutor(max_workers=os.cpu_count())

        futures = []
        current_logs = {
            mat["name"]: "Aguardando processamento..." for mat in materials_catalog
        }

        # Conversão do objeto Pydantic para dicionário para garantir a serialização (Pickle).
        # Sendo assim, evitamos falhas de IPC entre o processo pai e os workers.
        params_dict = params.dict()

        # Submissão das tarefas de otimização em paralelo.
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
            # Proteção de Memória (Anti-OOM): Monitoramento do consumo global de RAM.
            # Sendo assim, interrompemos o cálculo se o servidor atingir 90% de ocupação da memória.
            memory_usage = psutil.virtual_memory().percent
            if memory_usage > 90:
                if executor:
                    executor.shutdown(wait=False, cancel_futures=True)
                if manager:
                    manager.shutdown()
                # Interrupção preventiva por estouro de memória (OOM) para garantir a integridade do servidor.
                return OptimizationResponse(
                    is_structurally_stable=False,
                    status_message=f"Processamento interrompido: O modelo estrutural excedeu o limite de memória do servidor. Recomenda-se reduzir as dimensões ou o número de seções.",
                    total_weight=0,
                    members=[],
                    nodes={},
                )

            # Monitoramento de sinais de cancelamento ou desconexão do cliente.
            if request and await request.is_disconnected():
                raise asyncio.CancelledError("Desconexão do cliente.")

            # Coleta de atualizações de log de todos os workers ativos.
            while not queue.empty():
                try:
                    msg = queue.get_nowait()
                    current_logs[msg["worker_id"]] = msg["message"]
                except:
                    break

            # Verificação de tarefas concluídas para cálculo de progresso.
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

        # Consolidação dos resultados e seleção da solução de menor custo global.
        best_overall = None
        min_cost = float("inf")
        last_error = "Não foi possível encontrar uma solução válida para os parâmetros informados."

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
                status_message=f"Análise finalizada. O material {best_overall['material_name']} apresentou a solução mais econômica e segura.",
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
        # Encerramento rigoroso dos processos filhos para evitar 'zombies'.
        # Portanto, libertamos os recursos da CPU e memória imediatamente.
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
            status_message=f"Erro interno durante a análise estrutural: {str(e)}",
            total_weight=0,
            members=[],
            nodes={},
        )
    finally:
        if executor:
            executor.shutdown(wait=True)
        if manager:
            manager.shutdown()
