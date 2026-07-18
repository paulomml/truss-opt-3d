"""
Script de popularização inicial do banco de dados.

Substitui os antigos materials.csv e profiles.csv por registros
relacionais no PostgreSQL. Executado automaticamente na primeira
inicialização do container backend (via seed.sh no entrypoint).

Catálogo:
- 6 aços estruturais nacionais (NBR 8800 / NBR 7007)
- 32 perfis comerciais (cantoneiras L, tubos RHS, U enrijecido Ue)
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from core.database import SessionLocal, inicializar_banco
from db.modelos import Material, Perfil

_logger = logging.getLogger("seed")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# MATERIAIS: Aços estruturais nacionais (NBR 8800 / NBR 7007)
MATERIAIS_PADRAO = [
    {
        "nome": "A36",
        "norma_referencia": "ASTM A36",
        "observacao": "Aço carbono laminado — perfis L e U importados.",
        "e_gpa": 200.0,
        "g_gpa": 76.9,
        "nu": 0.30,
        "fy_mpa": 250.0,
        "fu_mpa": 400.0,
        "rho_kg_m3": 7850.0,
        "custo_kg": 8.45,
    },
    {
        "nome": "A572-Gr50",
        "norma_referencia": "ASTM A572 Gr.50",
        "observacao": "Alta resistência — tubos e perfis especiais.",
        "e_gpa": 200.0,
        "g_gpa": 76.9,
        "nu": 0.30,
        "fy_mpa": 345.0,
        "fu_mpa": 450.0,
        "rho_kg_m3": 7850.0,
        "custo_kg": 12.95,
    },
    {
        "nome": "MR250",
        "norma_referencia": "NBR 8800 / NBR 7007",
        "observacao": "Aço carbono nacional — equivalente ao A36. Gerdau MR250.",
        "e_gpa": 200.0,
        "g_gpa": 76.9,
        "nu": 0.30,
        "fy_mpa": 250.0,
        "fu_mpa": 400.0,
        "rho_kg_m3": 7850.0,
        "custo_kg": 8.80,
    },
    {
        "nome": "MR350",
        "norma_referencia": "NBR 8800 / NBR 7007",
        "observacao": "Alta resistência nacional — Gerdau MR350. Recomendado para banzos.",
        "e_gpa": 200.0,
        "g_gpa": 76.9,
        "nu": 0.30,
        "fy_mpa": 350.0,
        "fu_mpa": 450.0,
        "rho_kg_m3": 7850.0,
        "custo_kg": 10.50,
    },
    {
        "nome": "SAC300",
        "norma_referencia": "NBR 8800",
        "observacao": "Perfis formados a frio (Ue / RHS).",
        "e_gpa": 200.0,
        "g_gpa": 76.9,
        "nu": 0.30,
        "fy_mpa": 300.0,
        "fu_mpa": 420.0,
        "rho_kg_m3": 7850.0,
        "custo_kg": 9.70,
    },
    {
        "nome": "SAC350",
        "norma_referencia": "NBR 8800",
        "observacao": "Perfis formados a frio alta resistência (Ue espessura >= 2.65 mm).",
        "e_gpa": 200.0,
        "g_gpa": 76.9,
        "nu": 0.30,
        "fy_mpa": 350.0,
        "fu_mpa": 420.0,
        "rho_kg_m3": 7850.0,
        "custo_kg": 11.10,
    },
]


# PERFIS: Cantoneiras L, Tubos RHS, U enrijecido Ue
# Formato: (nome, familia, h, bf, d, t, Area, Ix, Iy, J, uso, chapa_ref)
# Unidades: dimensões em mm, áreas em m^2, inércias em m^4.

PERFIS_PADRAO = [
    # Cantoneiras de abas iguais (L): Montantes e Diagonais
    (
        "L19x3.18",
        "L",
        19,
        19,
        0,
        3.18,
        1.11e-4,
        3.20e-9,
        3.20e-9,
        3.74e-10,
        "Montante/Diagonal",
        "3/4 pol x 1/8 pol",
    ),
    (
        "L22x3.18",
        "L",
        22,
        22,
        0,
        3.18,
        1.30e-4,
        5.03e-9,
        5.03e-9,
        4.40e-10,
        "Montante/Diagonal",
        "7/8 pol x 1/8 pol",
    ),
    (
        "L25x3.18",
        "L",
        25,
        25,
        0,
        3.18,
        1.49e-4,
        7.49e-9,
        7.49e-9,
        5.02e-10,
        "Montante/Diagonal",
        "1 pol x 1/8 pol",
    ),
    (
        "L32x3.18",
        "L",
        32,
        32,
        0,
        3.18,
        1.92e-4,
        1.60e-8,
        1.60e-8,
        6.47e-10,
        "Montante/Diagonal",
        "1.1/4 pol x 1/8 pol",
    ),
    (
        "L38x3.18",
        "L",
        38,
        38,
        0,
        3.18,
        2.30e-4,
        2.75e-8,
        2.75e-8,
        7.65e-10,
        "Montante/Diagonal",
        "1.1/2 pol x 1/8 pol",
    ),
    (
        "L44x3.18",
        "L",
        44,
        44,
        0,
        3.18,
        2.67e-4,
        4.34e-8,
        4.34e-8,
        8.75e-10,
        "Montante/Diagonal",
        "1.3/4 pol x 1/8 pol",
    ),
    (
        "L51x3.18",
        "L",
        51,
        51,
        0,
        3.18,
        3.06e-4,
        6.55e-8,
        6.55e-8,
        9.95e-10,
        "Montante/Diagonal",
        "2 pol x 1/8 pol",
    ),
    (
        "L51x6.35",
        "L",
        51,
        51,
        0,
        6.35,
        5.81e-4,
        1.20e-7,
        1.20e-7,
        3.95e-9,
        "Montante/Diagonal",
        "2 pol x 1/4 pol",
    ),
    (
        "L64x6.35",
        "L",
        64,
        64,
        0,
        6.35,
        7.36e-4,
        2.49e-7,
        2.49e-7,
        5.10e-9,
        "Montante/Diagonal",
        "2.1/2 pol x 1/4 pol",
    ),
    (
        "L76x6.35",
        "L",
        76,
        76,
        0,
        6.35,
        8.85e-4,
        4.34e-7,
        4.34e-7,
        6.18e-9,
        "Banzo/Montante",
        "3 pol x 1/4 pol",
    ),
    # Tubos retangulares (RHS): Banzos e Montantes
    (
        "RHS50x30x2.00",
        "RHS",
        50,
        30,
        0,
        2.00,
        2.96e-4,
        5.60e-8,
        2.08e-8,
        5.50e-8,
        "Banzo/Montante",
        "Chapa 14",
    ),
    (
        "RHS50x30x1.50",
        "RHS",
        50,
        30,
        0,
        1.50,
        2.25e-4,
        4.36e-8,
        1.63e-8,
        4.25e-8,
        "Banzo/Montante",
        "Chapa 16",
    ),
    (
        "RHS60x40x2.00",
        "RHS",
        60,
        40,
        0,
        2.00,
        3.76e-4,
        1.11e-7,
        5.43e-8,
        1.28e-7,
        "Banzo/Montante",
        "Chapa 14",
    ),
    (
        "RHS60x40x2.50",
        "RHS",
        60,
        40,
        0,
        2.50,
        4.62e-4,
        1.33e-7,
        6.49e-8,
        1.61e-7,
        "Banzo/Montante",
        "Chapa 12",
    ),
    (
        "RHS80x40x2.00",
        "RHS",
        80,
        40,
        0,
        2.00,
        4.56e-4,
        2.45e-7,
        7.13e-8,
        1.97e-7,
        "Banzo/Montante",
        "Chapa 14",
    ),
    (
        "RHS80x40x3.00",
        "RHS",
        80,
        40,
        0,
        3.00,
        6.61e-4,
        3.43e-7,
        9.95e-8,
        3.02e-7,
        "Banzo/Montante",
        "Chapa 10",
    ),
    (
        "RHS100x50x2.00",
        "RHS",
        100,
        50,
        0,
        2.00,
        5.76e-4,
        4.66e-7,
        1.30e-7,
        3.34e-7,
        "Banzo",
        "Chapa 14",
    ),
    (
        "RHS100x50x3.00",
        "RHS",
        100,
        50,
        0,
        3.00,
        8.41e-4,
        6.59e-7,
        1.84e-7,
        5.13e-7,
        "Banzo",
        "Chapa 10",
    ),
    (
        "RHS120x60x3.00",
        "RHS",
        120,
        60,
        0,
        3.00,
        1.02e-3,
        1.13e-6,
        3.18e-7,
        8.16e-7,
        "Banzo",
        "Chapa 10",
    ),
    (
        "RHS150x75x3.00",
        "RHS",
        150,
        75,
        0,
        3.00,
        1.29e-3,
        2.26e-6,
        6.40e-7,
        1.32e-6,
        "Banzo",
        "Chapa 10",
    ),
    # U enrijecido (Ue): Banzos de tesouras
    ("Ue75x40x15x2.00", "Ue", 75, 40, 15, 2.00, 3.26e-4, 2.91e-7, 3.89e-8, 4.36e-10, "Banzo", "—"),
    ("Ue75x40x15x2.25", "Ue", 75, 40, 15, 2.25, 3.65e-4, 3.24e-7, 4.34e-8, 6.18e-10, "Banzo", "—"),
    ("Ue75x40x15x2.65", "Ue", 75, 40, 15, 2.65, 4.28e-4, 3.77e-7, 5.04e-8, 1.01e-9, "Banzo", "—"),
    ("Ue75x40x15x3.00", "Ue", 75, 40, 15, 3.00, 4.83e-4, 4.23e-7, 5.65e-8, 1.45e-9, "Banzo", "—"),
    ("Ue92x40x15x2.00", "Ue", 92, 40, 15, 2.00, 3.60e-4, 5.06e-7, 4.24e-8, 4.80e-10, "Banzo", "—"),
    ("Ue92x40x15x2.25", "Ue", 92, 40, 15, 2.25, 4.03e-4, 5.65e-7, 4.73e-8, 6.82e-10, "Banzo", "—"),
    ("Ue92x40x15x2.65", "Ue", 92, 40, 15, 2.65, 4.73e-4, 6.58e-7, 5.49e-8, 1.11e-9, "Banzo", "—"),
    ("Ue92x40x15x3.00", "Ue", 92, 40, 15, 3.00, 5.34e-4, 7.39e-7, 6.17e-8, 1.60e-9, "Banzo", "—"),
    (
        "Ue100x40x15x2.00",
        "Ue",
        100,
        40,
        15,
        2.00,
        3.76e-4,
        6.28e-7,
        4.38e-8,
        5.02e-10,
        "Banzo",
        "—",
    ),
    (
        "Ue100x40x15x2.25",
        "Ue",
        100,
        40,
        15,
        2.25,
        4.22e-4,
        7.02e-7,
        4.89e-8,
        7.13e-10,
        "Banzo",
        "—",
    ),
    ("Ue100x40x15x2.65", "Ue", 100, 40, 15, 2.65, 4.95e-4, 8.19e-7, 5.68e-8, 1.16e-9, "Banzo", "—"),
    ("Ue100x40x15x3.00", "Ue", 100, 40, 15, 3.00, 5.59e-4, 9.20e-7, 6.38e-8, 1.68e-9, "Banzo", "—"),
]


def popular_banco() -> None:
    """Cria tabelas e popula com dados padrão (idempotente)."""
    _logger.info("Inicializando esquema do banco de dados...")
    inicializar_banco()

    with SessionLocal() as sessao:
        # Materiais
        materiais_existentes = {m.nome for m in sessao.scalars(select(Material)).all()}
        for dados in MATERIAIS_PADRAO:
            if dados["nome"] not in materiais_existentes:
                sessao.add(Material(**dados))
                _logger.info(f"Material adicionado: {dados['nome']}")

        # Perfis
        perfis_existentes = {p.nome for p in sessao.scalars(select(Perfil)).all()}
        for nome, fam, h, bf, d, t, A, Ix, Iy, J, uso, chapa in PERFIS_PADRAO:
            if nome not in perfis_existentes:
                sessao.add(
                    Perfil(
                        nome=nome,
                        familia=fam,
                        h_mm=h,
                        bf_mm=bf,
                        d_mm=d,
                        t_mm=t,
                        area_m2=A,
                        ix_m4=Ix,
                        iy_m4=Iy,
                        j_m4=J,
                        uso_recomendado=uso,
                        chapa_referencia=chapa,
                    )
                )
                _logger.info(f"Perfil adicionado: {nome}")

        sessao.commit()

    _logger.info("Banco de dados populado com sucesso.")


if __name__ == "__main__":
    popular_banco()
