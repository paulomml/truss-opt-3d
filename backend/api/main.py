import os
import json
import asyncio
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from domain.models import TrussRequest, OptimizationResponse
from use_cases.optimize_truss import optimize_truss_use_case

# Entrypoint da API FastAPI.
# Abstrai a complexidade do motor FEA para consumo via HTTP/WebSocket.
app = FastAPI(title="3D Truss Optimizer API")

# Middleware CORS: Permitir todas as origens para facilitar o desenvolvimento e deploy em infra distribuída.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/optimize", response_model=OptimizationResponse)
async def optimize(request: TrussRequest, fastapi_req: Request):
    """
    Endpoint síncrono legado.
    Atenção: Sujeito a timeouts em modelos complexos. Preferir /api/ws/optimize.
    """
    try:
        result = await optimize_truss_use_case(request, fastapi_req)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/api/ws/optimize")
async def websocket_optimize(websocket: WebSocket):
    """
    Comunicação full-duplex para streaming de progresso do solver.
    Evita o overhead de polling HTTP e fornece feedback granular dos workers de multiprocessing.
    """
    await websocket.accept()

    async def run_optimizer(payload: dict):
        request_obj = TrussRequest(**payload)

        async def progress_callback(
            main_progress: float,
            current_logs: dict,
        ):
            # Streaming de metadados de progresso via WebSocket.
            # Permite que o frontend atualize a UI reativamente sem bloquear a main thread.
            await websocket.send_json(
                {
                    "type": "progress",
                    "data": {
                        "main_progress": main_progress,
                        "current_logs": current_logs,
                    },
                }
            )

        return await optimize_truss_use_case(
            request_obj, progress_callback=progress_callback
        )

    opt_task = None
    try:
        data = await websocket.receive_text()
        payload = json.loads(data)

        # Offload da otimização para uma task assíncrona.
        # Mantém a disponibilidade do socket para escutar sinais de interrupção (cancelamento) do cliente.
        opt_task = asyncio.create_task(run_optimizer(payload))

        # Task secundária para monitorar se o cliente envia sinais ou desconecta.
        listen_task = asyncio.create_task(websocket.receive_text())

        done, pending = await asyncio.wait(
            [opt_task, listen_task], return_when=asyncio.FIRST_COMPLETED
        )

        if opt_task in done:
            result = opt_task.result()
            # Dispatch do resultado final processado.
            await websocket.send_json({"type": "result", "data": result.dict()})
        else:
            # Se o listen_task terminar primeiro, houve cancelamento ou desconexão.
            if opt_task:
                opt_task.cancel()

    except WebSocketDisconnect:
        if opt_task and not opt_task.done():
            opt_task.cancel()
    except Exception as e:
        if opt_task and not opt_task.done():
            opt_task.cancel()
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        # Graceful cleanup: cancela tasks órfãs para evitar resource exhaustion no servidor.
        if opt_task and not opt_task.done():
            opt_task.cancel()


@app.get("/api/health")
async def health():
    """
    Verificação operacional da disponibilidade dos serviços de backend.
    """
    return {"status": "ok"}


# Provedor de ativos estáticos (SPA fallback) para produção.
# Prioridade de roteamento: API > Static Files.
public_dir = os.path.join(os.path.dirname(__file__), "..", "public")
if os.path.isdir(public_dir) and os.listdir(public_dir):
    app.mount("/", StaticFiles(directory=public_dir, html=True), name="static")
