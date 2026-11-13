"""Processamento dos CSVs de vendas (regras de negócio).

Este módulo usa apenas a biblioteca padrão do Python, de propósito:
deixa a imagem do Cloud Run pequena, o cold start rápido e o código fácil de
explicar na apresentação.

Formato esperado do CSV (cabeçalho obrigatório):
    data,produto,quantidade,preco_unitario
    2025-03-01,Camiseta,2,49.90

Aceita separador "," ou ";", datas AAAA-MM-DD ou DD/MM/AAAA e preço com
ponto ou vírgula decimal.
"""
import csv
import io
import unicodedata
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

COLUNAS_OBRIGATORIAS = ("data", "produto", "quantidade", "preco_unitario")
MAX_ERROS_LISTADOS = 20
TOP_N = 5


def _normalizar(texto: str) -> str:
    """minúsculas, sem acentos e sem espaços nas pontas: 'Preço ' -> 'preco'."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.strip().lower().replace(" ", "_")


def _decodificar(conteudo: bytes) -> str:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return conteudo.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Não foi possível ler o arquivo (codificação desconhecida).")


def _parse_data(valor: str) -> date:
    valor = valor.strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(valor, formato).date()
        except ValueError:
            continue
    raise ValueError(f"data inválida '{valor}' (use AAAA-MM-DD ou DD/MM/AAAA)")


def _parse_decimal(valor: str, campo: str) -> Decimal:
    limpo = valor.strip().replace("R$", "").replace(" ", "")
    # "1.234,50" -> "1234.50" | "12,50" -> "12.50" | "12.50" -> "12.50"
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(limpo)
    except InvalidOperation:
        raise ValueError(f"{campo} inválido '{valor}'")
    if not numero.is_finite():
        raise ValueError(f"{campo} inválido '{valor}'")
    return numero


def _ler_linhas(texto: str):
    """Devolve (leitor, cabecalho_normalizado) detectando o separador."""
    linhas = texto.splitlines()
    if not linhas or not linhas[0].strip():
        raise ValueError("arquivo vazio")
    primeira = linhas[0]
    delimitador = ";" if primeira.count(";") > primeira.count(",") else ","
    leitor = csv.reader(io.StringIO(texto), delimiter=delimitador)
    cabecalho = next(leitor)
    return leitor, [_normalizar(c) for c in cabecalho]


def analisar(arquivos: dict) -> dict:
    """Processa um ou mais CSVs e devolve os indicadores consolidados.

    arquivos: {"nome.csv": b"conteúdo", ...}
    """
    total = Decimal("0")
    total_itens = Decimal("0")
    por_produto = defaultdict(lambda: {"quantidade": Decimal("0"), "receita": Decimal("0")})
    por_dia = defaultdict(lambda: Decimal("0"))
    validos = 0
    invalidos = 0
    erros = []

    def registrar_erro(arquivo, linha, motivo):
        nonlocal invalidos
        invalidos += 1
        if len(erros) < MAX_ERROS_LISTADOS:
            erros.append({"arquivo": arquivo, "linha": linha, "motivo": motivo})

    for nome, conteudo in arquivos.items():
        try:
            leitor, cabecalho = _ler_linhas(_decodificar(conteudo))
        except ValueError as exc:
            registrar_erro(nome, 1, str(exc))
            continue

        faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in cabecalho]
        if faltando:
            registrar_erro(nome, 1, "colunas ausentes: " + ", ".join(faltando))
            continue

        idx = {c: cabecalho.index(c) for c in COLUNAS_OBRIGATORIAS}

        for numero_linha, linha in enumerate(leitor, start=2):
            if not any(c.strip() for c in linha):
                continue  # linha em branco
            try:
                if len(linha) < len(cabecalho):
                    raise ValueError("linha com colunas faltando")
                data = _parse_data(linha[idx["data"]])
                produto = linha[idx["produto"]].strip()
                if not produto:
                    raise ValueError("produto vazio")
                quantidade = _parse_decimal(linha[idx["quantidade"]], "quantidade")
                preco = _parse_decimal(linha[idx["preco_unitario"]], "preco_unitario")
                if quantidade <= 0 or quantidade != quantidade.to_integral_value():
                    raise ValueError("quantidade deve ser um inteiro positivo")
                if preco < 0:
                    raise ValueError("preco_unitario não pode ser negativo")
            except ValueError as exc:
                registrar_erro(nome, numero_linha, str(exc))
                continue

            valor = quantidade * preco
            validos += 1
            total += valor
            total_itens += quantidade
            por_produto[produto]["quantidade"] += quantidade
            por_produto[produto]["receita"] += valor
            por_dia[data] += valor

    ranking = sorted(
        por_produto.items(),
        key=lambda kv: (kv[1]["quantidade"], kv[1]["receita"]),
        reverse=True,
    )[:TOP_N]

    return {
        "arquivos_processados": len(arquivos),
        "registros_validos": validos,
        "registros_invalidos": invalidos,
        "total_vendas": float(round(total, 2)),
        "total_itens": int(total_itens),
        "ticket_medio": float(round(total / validos, 2)) if validos else 0.0,
        "top_produtos": [
            {
                "produto": nome,
                "quantidade": int(v["quantidade"]),
                "receita": float(round(v["receita"], 2)),
            }
            for nome, v in ranking
        ],
        "vendas_por_dia": [
            {"data": d.isoformat(), "total": float(round(v, 2))}
            for d, v in sorted(por_dia.items())
        ],
        "erros": erros,
    }
