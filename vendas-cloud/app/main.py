"""API do Sistema de Análise de Vendas na Nuvem (Google Cloud).

Endpoints:
    GET  /                  -> dashboard web
    GET  /health            -> verificação de saúde
    POST /api/upload        -> envia um CSV (salva no Cloud Storage e processa)
    GET  /api/arquivos      -> lista os CSVs armazenados
    GET  /api/relatorio     -> indicadores (de um arquivo ou de todos)
    GET  /docs              -> documentação interativa (Swagger) gerada pelo FastAPI
"""
import os
import secrets
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.analytics import analisar
from app.storage import nome_seguro, obter_armazenamento

TAMANHO_MAXIMO = 5 * 1024 * 1024  # 5 MB por arquivo
PASTA_ESTATICA = Path(__file__).parent / "static"

app = FastAPI(
    title="Análise de Vendas na Nuvem",
    description="Envia CSVs de vendas para o Cloud Storage e calcula indicadores.",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=PASTA_ESTATICA), name="static")

_armazenamento = None


def armazenamento():
    """Cria o cliente de storage uma única vez (reaproveitado entre requisições)."""
    global _armazenamento
    if _armazenamento is None:
        _armazenamento = obter_armazenamento()
    return _armazenamento


def _checar_chave(x_api_key: Optional[str]) -> None:
    """Se API_KEY estiver configurada (via Secret Manager), exige no upload."""
    esperada = os.getenv("API_KEY")
    if not esperada:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, esperada):
        raise HTTPException(status_code=401, detail="Chave de API ausente ou inválida.")


@app.get("/", include_in_schema=False)
def pagina_inicial():
    return FileResponse(PASTA_ESTATICA / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/upload")
async def upload(
    arquivo: UploadFile = File(...),
    x_api_key: Optional[str] = Header(default=None),
):
    _checar_chave(x_api_key)

    if not (arquivo.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Envie um arquivo com extensão .csv.")

    conteudo = await arquivo.read(TAMANHO_MAXIMO + 1)
    if len(conteudo) > TAMANHO_MAXIMO:
        raise HTTPException(status_code=413, detail="Arquivo maior que 5 MB.")
    if not conteudo.strip():
        raise HTTPException(status_code=400, detail="O arquivo está vazio.")

    # Valida ANTES de gravar: arquivo sem nenhuma linha válida não vai para o bucket.
    relatorio = analisar({arquivo.filename: conteudo})
    if relatorio["registros_validos"] == 0:
        raise HTTPException(
            status_code=422,
            detail={
                "mensagem": "Nenhum registro válido encontrado no CSV.",
                "erros": relatorio["erros"],
            },
        )

    nome = nome_seguro(arquivo.filename)
    armazenamento().salvar(nome, conteudo)
    return {"arquivo": nome, "relatorio": relatorio}


@app.get("/api/arquivos")
def listar_arquivos():
    return {"arquivos": armazenamento().listar()}


@app.get("/api/relatorio")
def relatorio(arquivo: Optional[str] = Query(default=None, description="Nome do arquivo; vazio = todos")):
    store = armazenamento()
    if arquivo:
        try:
            conteudos = {arquivo: store.ler(arquivo)}
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    else:
        conteudos = {item["nome"]: store.ler(item["nome"]) for item in store.listar()}
        if not conteudos:
            raise HTTPException(status_code=404, detail="Nenhum arquivo enviado ainda.")
    return analisar(conteudos)
