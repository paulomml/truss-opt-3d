import os
from fastapi import FastAPI, HTTPException, Request
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
    Ponto de entrada para o processamento do design estrutural e otimização.
    Logo, a requisição é encaminhada para o caso de uso de otimização de custo e estabilidade.
    """
    try:
        result = await optimize_truss_use_case(request, fastapi_req)
        return result
    except Exception as e:
        # Tratamento de exceções críticas para garantir a integridade do serviço de cálculo.
        raise HTTPException(status_code=500, detail=str(e))


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
