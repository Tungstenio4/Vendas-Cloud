"""Camada de armazenamento.

- Na nuvem (variável BUCKET_NAME definida): usa o Google Cloud Storage.
  As credenciais NÃO ficam no código: no Cloud Run a aplicação assume a
  identidade da Service Account do serviço (Application Default Credentials).
- Local (sem BUCKET_NAME): grava na pasta ./local_bucket, só para desenvolver
  e testar antes de publicar.
"""
import os
import re
from datetime import datetime, timezone
from pathlib import Path


def nome_seguro(nome_original: str) -> str:
    """Remove caminhos e caracteres perigosos e prefixa com data/hora UTC."""
    base = os.path.basename((nome_original or "").replace("\\", "/"))
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base)[:100] or "vendas.csv"
    carimbo = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{carimbo}_{base}"


class ArmazenamentoLocal:
    def __init__(self, pasta: str = "local_bucket"):
        self.pasta = Path(pasta)
        self.pasta.mkdir(parents=True, exist_ok=True)

    def salvar(self, nome: str, conteudo: bytes) -> None:
        (self.pasta / nome).write_bytes(conteudo)

    def listar(self) -> list:
        itens = []
        for p in self.pasta.iterdir():
            if p.is_file():
                st = p.stat()
                itens.append({
                    "nome": p.name,
                    "tamanho": st.st_size,
                    "atualizado": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                })
        return sorted(itens, key=lambda i: i["nome"], reverse=True)

    def ler(self, nome: str) -> bytes:
        caminho = self.pasta / os.path.basename(nome)
        if not caminho.is_file():
            raise FileNotFoundError(nome)
        return caminho.read_bytes()


class ArmazenamentoGCS:
    def __init__(self, bucket_name: str):
        from google.cloud import storage  # import tardio: não exigido no modo local

        self.bucket = storage.Client().bucket(bucket_name)

    def salvar(self, nome: str, conteudo: bytes) -> None:
        self.bucket.blob(nome).upload_from_string(conteudo, content_type="text/csv")

    def listar(self) -> list:
        itens = [
            {
                "nome": b.name,
                "tamanho": b.size,
                "atualizado": b.updated.isoformat() if b.updated else None,
            }
            for b in self.bucket.list_blobs()
        ]
        return sorted(itens, key=lambda i: i["nome"], reverse=True)

    def ler(self, nome: str) -> bytes:
        blob = self.bucket.blob(nome)
        if not blob.exists():
            raise FileNotFoundError(nome)
        return blob.download_as_bytes()


def obter_armazenamento():
    bucket = os.getenv("BUCKET_NAME")
    if bucket:
        return ArmazenamentoGCS(bucket)
    return ArmazenamentoLocal()
