# Modelo do Relatório Técnico (PDF, 4 a 6 páginas)

Preencham os campos entre [colchetes]. Cada seção corresponde a um item exigido no enunciado.
Cole os prints nos lugares indicados e exporte para PDF.

---

## 1. Identificação
**Título:** Sistema de Análise de Vendas na Nuvem
**Disciplina:** Cloud Computing  **Professor:** [nome]  **Data:** [data]
**Integrantes:** [nome 1], [nome 2], [nome 3], [nome 4], [nome 5]
**URL do sistema:** [https://vendas-cloud-xxxx.a.run.app]  **Repositório:** [link GitHub]

## 2. Problema e objetivo
Pequenos comércios registram vendas em planilhas e CSVs espalhados em computadores
diferentes, o que dificulta consolidar resultados, descobrir os produtos mais vendidos e
manter os dados seguros. **Objetivo:** permitir enviar CSVs de vendas pela Internet,
armazená-los de forma persistente na nuvem e gerar automaticamente indicadores e relatório.
**Por que nuvem:** acesso de qualquer lugar, armazenamento durável, processamento sob
demanda sem servidor próprio e custo proporcional ao uso.

## 3. Funcionalidades
- Upload de CSV com validação (extensão, tamanho máx. 5 MB, colunas obrigatórias, linhas inválidas).
- Armazenamento em bucket privado; listagem dos arquivos enviados.
- Cálculo de total de vendas, itens vendidos, ticket médio, top 5 produtos e vendas por dia.
- Relatório por arquivo ou consolidado; lista das linhas rejeitadas com o motivo.
- API REST documentada (Swagger em `/docs`) e dashboard web.

## 4. Arquitetura
[Cole aqui o diagrama. Há uma versão em texto no README; redesenhem no draw.io ou Excalidraw.]

Fluxo: navegador → HTTPS → Cloud Run → (grava/lê) Cloud Storage; Cloud Run lê a chave do
Secret Manager; o acesso ao bucket usa a Service Account do serviço.

**Modelos de serviço:** PaaS (Cloud Run, Cloud Storage, Secret Manager): o provedor gerencia
servidores, SO e escala; SaaS (Console do Google Cloud). Não usamos IaaS.

## 5. Serviços utilizados e justificativas
| Serviço | Função | Justificativa |
|---|---|---|
| Projeto GCP | agrupa e isola os recursos (equivalente ao Resource Group) | organização, permissões e faturamento por projeto |
| Cloud Storage | guarda os CSVs | armazenamento de objetos durável, cota gratuita |
| Cloud Run | executa API, processamento e dashboard | serverless, escala a zero, cota gratuita |
| Secret Manager | guarda a chave de API | evita credenciais no código |
| IAM / Service Account | identidade do app | permissão mínima, sem chaves em arquivo |
| Cloud Build / Artifact Registry | build e imagem do contêiner | usados pelo `gcloud run deploy --source` |

**Sobre a troca do Azure:** [Explicar: instabilidade do Azure no período do projeto, aprovação
do professor em (data), e a tabela de equivalência Azure → GCP do README.]

## 6. Tecnologias
Python 3.12, FastAPI, Uvicorn, google-cloud-storage, HTML/CSS/JavaScript, Docker, gcloud CLI, Git/GitHub.

## 7. Evidências da implementação e dos testes
Incluir prints legendados:
1. Projeto criado no console
2. Bucket (configurações: privado, região)
3. Serviço Cloud Run em execução (URL)
4. Permissões IAM da Service Account
5. Segredo no Secret Manager (sem mostrar o valor)
6. Dashboard com um relatório gerado
7. Objeto gravado no bucket após o upload
8. Logs do Cloud Run
9. Testes de entrada inválida (HTTP 422, 401, 400)
10. Orçamento/alerta de custo e a página de consumo

Tabela de resultados dos testes: [copiar a tabela do README e preencher "obtido" e "OK/falha"].

## 8. Segurança, consumo e custos
- **Credenciais:** nenhuma no código; chave de API no Secret Manager; app acessa o bucket via Service Account.
- **Menor privilégio:** a Service Account tem acesso só ao bucket do projeto e ao segredo.
- **Bucket privado** com *public access prevention* e acesso uniforme.
- **Validações:** extensão, tamanho, cabeçalho, tipos dos campos, nome de arquivo sanitizado.
- **Transporte:** HTTPS gerenciado pelo Cloud Run.
- **Limites de custo:** `--max-instances 2` e alerta de orçamento.
- **Consumo observado:** [requisições, GB armazenados, print da tela de faturamento].
- **Estimativa de custos:** [dentro da cota gratuita = R$ 0; colocar print da Calculadora de Preços
  com uso hipotético, ex.: 10 mil requisições/mês e 1 GB armazenado].
- **Limitações encontradas (pay-to-use):** [ex.: exigência de cartão de crédito para ativar a conta
  de faturamento; cotas gratuitas só em regiões dos EUA; relatar o que o grupo vivenciou].

## 9. Conclusão, dificuldades e melhorias
**Conclusão:** [o que o grupo aprendeu sobre armazenamento, processamento e integração na nuvem].
**Dificuldades:** [reais do grupo: troca de provedor, permissões do Cloud Build, ...].
**Melhorias:** login de usuários (Identity Platform/Firebase Auth), banco de dados
(Firestore/BigQuery) para consultas maiores, processamento automático com gatilho no upload
(Eventarc), gráficos mais ricos, exportação do relatório em PDF, domínio próprio.

---
**Checklist de entrega:** [ ] Relatório PDF  [ ] Repositório sem credenciais  [ ] Prints de
evidências  [ ] Aprovação do professor para usar GCP  [ ] Todos sabem explicar o código e a arquitetura
