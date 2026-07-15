"""
Configurações globais da aplicação TRUSS-OPT 3D.

Todas as configurações sensíveis são lidas de variáveis de ambiente, com
valores padrão adequados para o desenvolvimento local. Em produção, o
docker-compose injeta as variáveis corretas para cada container.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracoes(BaseSettings):
    """Configurações centralizadas via pydantic-settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Aplicação
    nome_app: str = "TRUSS-OPT 3D API"
    versao_app: str = "1.0.0"
    ambiente: str = Field(default="desenvolvimento", description="desenvolvimento | producao")
    depurar: bool = False
    origens_cors: str = Field(
        default="*",
        description="Lista de origens CORS separadas por vírgula.",
    )

    # Banco de dados PostgreSQL
    postgres_usuario: str = "truss"
    postgres_senha: str = "truss"
    postgres_host: str = "postgres"
    postgres_porta: int = 5432
    postgres_banco: str = "truss_opt"
    echo_sql: bool = False

    # Redis (broker Celery + cache)
    redis_host: str = "redis"
    redis_porta: int = 6379
    redis_db: int = 0

    # Celery
    celery_tempo_limite_duro: int = 1800  # 30 minutos por tarefa
    celery_tempo_limite_suave: int = 1500
    celery_max_concorrencia: int = 1  # Análises MEF são pesadas: 1 por worker

    # Limite de memória (segurança contra OOM)
    limite_memoria_percentual: float = Field(
        default=85.0,
        description="Interrompe a otimização se a RAM do container exceder este percentual.",
    )

    # Algoritmo Genético (DEAP)
    ag_populacao_tamanho: int = 30
    ag_geracoes: int = 25
    ag_probabilidade_cruzamento: float = 0.7
    ag_probabilidade_mutacao: float = 0.2
    ag_indice_torneio: int = 3
    ag_alfa_cruzamento: float = 0.5  # CX blended
    ag_probabilidade_gaussiana: float = 0.5
    ag_mu_mutacao: float = 0.0
    ag_sigma_mutacao: float = 0.2
    ag_penalidade_violacao_normativa: float = Field(
        default=1.0e6,
        description="Penalidade por violação de norma (R$): aplicada a cada barra com U > 1.0.",
    )
    ag_penalidade_diversidade_perfis: float = Field(
        default=5.0e3,
        description="Penalidade por excesso de perfis distintos (R$): incentiva padronização.",
    )
    ag_max_perfis_distintos: int = 4
    ag_usar_refinamento_local: bool = Field(
        default=True,
        description="Ativa busca local (hill climbing) após cada geração do GA: algoritmo memético.",
    )

    # Verificações normativas
    nbr_flecha_limite: float = 250.0  # L/250 para ELS
    nbr_esbeltez_max_compressao: float = 200.0  # NBR 8800 5.3.4.1
    nbr_esbeltez_max_tracao: float = 300.0  # NBR 8800 5.2.8.1
    nbr_gamma_a1: float = 1.10  # NBR 8800: combinações normais
    nbr_carga_manutencao_kn: float = 1.0  # NBR 6120 item 6.4

    @property
    def database_url(self) -> str:
        """Monta a URL de conexão SQLAlchemy para PostgreSQL."""
        return (
            f"postgresql+psycopg2://{self.postgres_usuario}:{self.postgres_senha}"
            f"@{self.postgres_host}:{self.postgres_porta}/{self.postgres_banco}"
        )

    @property
    def database_url_assincrona(self) -> str:
        """URL assíncrona (utilizada em seeds e migrations rápidas)."""
        return (
            f"postgresql+psycopg2://{self.postgres_usuario}:{self.postgres_senha}"
            f"@{self.postgres_host}:{self.postgres_porta}/{self.postgres_banco}"
        )

    @property
    def redis_url(self) -> str:
        """URL de conexão com Redis."""
        return f"redis://{self.redis_host}:{self.redis_porta}/{self.redis_db}"

    @property
    def cors_lista(self) -> List[str]:
        """Converte a string CSV de origens em lista."""
        if self.origens_cors == "*":
            return ["*"]
        return [s.strip() for s in self.origens_cors.split(",") if s.strip()]


@lru_cache
def obter_configuracoes() -> Configuracoes:
    """Singleton de configuração (cacheado para performance)."""
    return Configuracoes()


# Instância global de configuração importável em todo o backend.
configuracoes = obter_configuracoes()
