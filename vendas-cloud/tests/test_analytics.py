"""Testes das regras de negócio. Execute com:  python -m unittest discover -s tests -v"""
import tempfile
import unittest
from pathlib import Path

from app.analytics import analisar
from app.storage import ArmazenamentoLocal, nome_seguro

RAIZ = Path(__file__).resolve().parent.parent / "dados_exemplo"


def ler(nome: str) -> bytes:
    return (RAIZ / nome).read_bytes()


class TestAnalise(unittest.TestCase):
    def test_csv_valido_totais(self):
        r = analisar({"a.csv": ler("vendas_exemplo.csv")})
        self.assertEqual(r["registros_validos"], 14)
        self.assertEqual(r["registros_invalidos"], 0)
        self.assertEqual(r["total_itens"], 48)
        # soma conferida manualmente
        self.assertAlmostEqual(r["total_vendas"], 3295.00, places=2)

    def test_top_produto_por_quantidade(self):
        r = analisar({"a.csv": ler("vendas_exemplo.csv")})
        self.assertEqual(r["top_produtos"][0]["produto"], "Meia Esportiva")
        self.assertEqual(r["top_produtos"][0]["quantidade"], 18)
        self.assertEqual(r["top_produtos"][1]["produto"], "Camiseta Básica")
        self.assertLessEqual(len(r["top_produtos"]), 5)

    def test_vendas_por_dia_ordenadas(self):
        r = analisar({"a.csv": ler("vendas_exemplo.csv")})
        datas = [d["data"] for d in r["vendas_por_dia"]]
        self.assertEqual(datas, sorted(datas))
        self.assertEqual(len(datas), 7)

    def test_formato_brasileiro(self):
        r = analisar({"br.csv": ler("vendas_formato_br.csv")})
        self.assertEqual(r["registros_validos"], 3)
        self.assertAlmostEqual(r["total_vendas"], 6 * 35 + 3 * 49.90 + 159.90, places=2)

    def test_linhas_invalidas_sao_reportadas(self):
        r = analisar({"e.csv": ler("vendas_com_erros.csv")})
        self.assertEqual(r["registros_validos"], 2)
        self.assertEqual(r["registros_invalidos"], 4)
        self.assertEqual({e["linha"] for e in r["erros"]}, {3, 4, 5, 6})

    def test_cabecalho_invalido(self):
        r = analisar({"x.csv": ler("vendas_cabecalho_invalido.csv")})
        self.assertEqual(r["registros_validos"], 0)
        self.assertIn("colunas ausentes", r["erros"][0]["motivo"])

    def test_arquivo_vazio(self):
        r = analisar({"v.csv": b""})
        self.assertEqual(r["registros_validos"], 0)
        self.assertEqual(r["erros"][0]["motivo"], "arquivo vazio")

    def test_consolidado_soma_arquivos(self):
        um = analisar({"a.csv": ler("vendas_exemplo.csv")})
        dois = analisar({"b.csv": ler("vendas_formato_br.csv")})
        junto = analisar({"a.csv": ler("vendas_exemplo.csv"), "b.csv": ler("vendas_formato_br.csv")})
        self.assertAlmostEqual(junto["total_vendas"], um["total_vendas"] + dois["total_vendas"], places=2)
        self.assertEqual(junto["arquivos_processados"], 2)

    def test_latin1(self):
        bruto = "data,produto,quantidade,preco_unitario\n2025-01-01,Calça,1,10.00\n".encode("latin-1")
        r = analisar({"l.csv": bruto})
        self.assertEqual(r["registros_validos"], 1)
        self.assertEqual(r["top_produtos"][0]["produto"], "Calça")

    def test_sem_validos_nao_divide_por_zero(self):
        r = analisar({"x.csv": ler("vendas_cabecalho_invalido.csv")})
        self.assertEqual(r["ticket_medio"], 0.0)


class TestArmazenamentoLocal(unittest.TestCase):
    def test_gravar_listar_ler(self):
        with tempfile.TemporaryDirectory() as pasta:
            loja = ArmazenamentoLocal(pasta)
            loja.salvar("teste.csv", b"abc")
            self.assertEqual([i["nome"] for i in loja.listar()], ["teste.csv"])
            self.assertEqual(loja.ler("teste.csv"), b"abc")

    def test_arquivo_inexistente(self):
        with tempfile.TemporaryDirectory() as pasta:
            with self.assertRaises(FileNotFoundError):
                ArmazenamentoLocal(pasta).ler("nao_existe.csv")

    def test_path_traversal_bloqueado(self):
        with tempfile.TemporaryDirectory() as pasta:
            loja = ArmazenamentoLocal(pasta)
            with self.assertRaises(FileNotFoundError):
                loja.ler("../../etc/passwd")

    def test_nome_seguro(self):
        nome = nome_seguro("../../segredo vendas?.csv")
        self.assertNotIn("/", nome)
        self.assertNotIn("..", nome)
        self.assertTrue(nome.endswith("segredo_vendas_.csv"))


if __name__ == "__main__":
    unittest.main()
