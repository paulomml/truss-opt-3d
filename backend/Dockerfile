FROM python:3.11-slim

WORKDIR /app

# Configuração das dependências do sistema operacional para suporte aos cálculos matriciais do backend.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Instalação das bibliotecas de análise estrutural e processamento de dados via gerenciador de pacotes pip.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Implantação da lógica de domínio, modelos e infraestrutura no ambiente isolado.
COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
