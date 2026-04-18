import os
import json
import asyncio
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from domain.models import TrussRequest, OptimizationResponse
from use_cases.optimize_truss import optimize_truss_use_case

# Inicialização da interface de comunicação para processamento das requisições estruturais.
app = FastAPI(title="3D Truss Optimizer API")

# Configuração do middleware de segurança para permitir o tráfego entre diferentes origens (CORS).
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
    Ponto de entrada legacional para o processamento do design estrutural.
    Recomenda-se o uso do endpoint WebSocket para feedback em tempo real.
    """
    try:
        result = await optimize_truss_use_case(request, fastapi_req)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/api/ws/optimize")
async def websocket_optimize(websocket: WebSocket):
    """
    Canal de comunicação bidirecional para otimização estrutural em tempo real.
    Sendo assim, o sistema permite o monitoramento granular do progresso e a detecção imediata de instabilidades de conexão.
    """
    await websocket.accept()

    async def run_optimizer(payload: dict):
        # Conversão do payload bruto para o modelo de domínio validado.
        request_obj = TrussRequest(**payload)

        async def progress_callback(
            main_progress: float,
            current_logs: dict,
        ):
            # Envio de metadados de progresso enriquecidos para a UI do cliente via WebSocket.
            # Sendo assim, o frontend pode exibir o estado de cada núcleo de processamento.
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
        # Aguarda a mensagem inicial contendo as configurações da treliça.
        data = await websocket.receive_text()
        # Deserialização dos parâmetros geométricos.
        # Logo, o sistema valida a integridade dos dados antes de iniciar o solver matricial.
        payload = json.loads(data)

        # Execução assíncrona da rotina de otimização.
        # Portanto, o servidor mantém a capacidade de resposta para sinais de cancelamento durante o cálculo pesado.
        opt_task = asyncio.create_task(run_optimizer(payload))

        # Task secundária para monitorar se o cliente envia sinais ou desconecta.
        listen_task = asyncio.create_task(websocket.receive_text())

        done, pending = await asyncio.wait(
            [opt_task, listen_task], return_when=asyncio.FIRST_COMPLETED
        )

        if opt_task in done:
            result = opt_task.result()
            # Encaminha o resultado final da otimização estável.
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
        # Garante a liberação de recursos e interrupção de tarefas órfãs.
        # Sendo assim, preserva-se a disponibilidade computacional para novas requisições.
        if opt_task and not opt_task.done():
            opt_task.cancel()


@app.get("/api/health")
async def health():
    """
    Verificação operacional da disponibilidade dos serviços de backend.
    """
    return {"status": "ok"}


# Provedor de arquivos estáticos para a interface do usuário em ambiente de produção.
# Portanto, as rotas da API possuem prioridade de roteamento sobre os ativos do frontend.
public_dir = os.path.join(os.path.dirname(__file__), "..", "public")
if os.path.isdir(public_dir) and os.listdir(public_dir):
    app.mount("/", StaticFiles(directory=public_dir, html=True), name="static")
