# Sistema de Análise de Vendas na Nuvem (Google Cloud + Python)

Projeto final de Cloud Computing (Projeto 2). O usuário envia arquivos CSV de vendas
pela Internet; os arquivos são gravados no **Cloud Storage**, processados no **Cloud Run**
e o resultado (total de vendas, produtos mais vendidos, vendas por dia, ticket médio e
linhas rejeitadas) aparece num dashboard web. A API tem documentação interativa em `/docs`.

> **Atenção:** o enunciado original pede Microsoft Azure. Antes de entregar, avisem o
> professor que o grupo usou o Google Cloud (o enunciado prevê comunicar restrições de
> acesso) e peçam a aprovação por escrito/e-mail. Guardem essa mensagem.

## Equivalência Azure → Google Cloud

| Requisito do enunciado | Azure (sugerido) | Google Cloud (usado aqui) |
|---|---|---|
| R1 Resource Group | Resource Group | **Projeto (Project)** do GCP |
| R2 Armazenamento | Blob Storage | **Cloud Storage** (bucket) |
| R3 Processamento | Azure Functions / App Service | **Cloud Run** (contêiner serverless, PaaS) |
| R4 Interface Web / API | Static Web Apps | Dashboard servido pelo próprio Cloud Run + API REST (Swagger em `/docs`) |
| R6 Segredos | Key Vault | **Secret Manager** |
| R6 Identidade/permissões | Managed Identity / RBAC | **Service Account + IAM** |
| R6 Custos | Cost Management | **Billing > Budgets & alerts** |

## Arquitetura

```
 Usuário (navegador / curl)
        │  HTTPS
        ▼
 ┌──────────────────────────── Projeto GCP (≈ Resource Group) ───────────────────────────┐
 │  Cloud Run  "vendas-cloud"   (PaaS, FastAPI)                                            │
 │   ├─ GET  /            dashboard (HTML/JS)                                              │
 │   ├─ POST /api/upload  valida CSV ──► grava no Cloud Storage                            │
 │   ├─ GET  /api/arquivos lista objetos do bucket                                         │
 │   └─ GET  /api/relatorio lê CSVs do bucket ──► calcula indicadores (processamento)      │
 │        │ identidade: Service Account "vendas-app" (sem chave no código)                 │
 │        ├──► Cloud Storage  bucket gs://vendas-<projeto>   (dados persistentes)          │
 │        └──► Secret Manager segredo "vendas-api-key"       (chave exigida no upload)     │
 └─────────────────────────────────────────────────────────────────────────────────────────┘
```

Modelos de serviço: **PaaS** (Cloud Run, Cloud Storage, Secret Manager — o grupo não gerencia
servidores) e **SaaS** (Console do Google Cloud). Não há IaaS (nenhuma VM).

## Estrutura do repositório

```
app/main.py          API FastAPI (rotas, validações, chave de API)
app/analytics.py     regras de negócio / processamento dos CSVs
app/storage.py       Cloud Storage (nuvem) ou pasta local (desenvolvimento)
app/static/index.html dashboard
dados_exemplo/       CSVs para teste (válido, formato BR, com erros, cabeçalho inválido)
tests/               testes automatizados
Dockerfile           imagem do Cloud Run
```

## 1. Rodar localmente (opcional, antes de publicar)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m unittest discover -s tests -t . -v         # testes
uvicorn app.main:app --reload                        # http://127.0.0.1:8000
```

Sem a variável `BUCKET_NAME`, os arquivos vão para `./local_bucket`. Isso serve só para
desenvolver: **a entrega exige o app rodando no Google Cloud**.

## 2. Publicar no Google Cloud (pelo Cloud Shell, sem instalar nada)

Crie a conta em <https://console.cloud.google.com>. O Google exige uma conta de
faturamento com cartão para ativar o teste gratuito e o nível "Always Free"; ele só cobra se
vocês confirmarem o upgrade para conta paga ou ultrapassarem as cotas depois disso.
Confirmem as regras atuais em <https://cloud.google.com/free>.

1. No console, crie um projeto (ex.: `vendas-cloud-grupoX`). Abra o **Cloud Shell** (ícone `>_`).
2. Envie esta pasta para o Cloud Shell (ou `git clone` do repositório do grupo) e entre nela.
3. Rode (troque o ID do projeto):

```bash
gcloud config set project SEU_PROJECT_ID
export PROJECT_ID=$(gcloud config get-value project)
export REGION=us-central1            # região elegível ao Always Free do Cloud Storage
export BUCKET=vendas-$PROJECT_ID
export SA=vendas-app@$PROJECT_ID.iam.gserviceaccount.com

# APIs usadas
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com storage.googleapis.com

# R2 - bucket privado
gcloud storage buckets create gs://$BUCKET --location=$REGION \
  --uniform-bucket-level-access --public-access-prevention

# R6 - identidade própria do app com permissão mínima (só neste bucket)
gcloud iam service-accounts create vendas-app --display-name="App de vendas"
gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
  --member="serviceAccount:$SA" --role="roles/storage.objectAdmin"

# R6 - chave de API no Secret Manager (não aparece no código)
read -s -p "Defina a chave de API: " CHAVE; echo
printf '%s' "$CHAVE" | gcloud secrets create vendas-api-key --data-file=-
gcloud secrets add-iam-policy-binding vendas-api-key \
  --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor"

# R3/R4 - build + deploy do Cloud Run (responda "Y" se pedir para criar o repositório)
gcloud run deploy vendas-cloud --source . --region $REGION \
  --service-account $SA \
  --set-env-vars BUCKET_NAME=$BUCKET \
  --set-secrets API_KEY=vendas-api-key:latest \
  --allow-unauthenticated --max-instances 2 --memory 512Mi
```

O comando imprime a **URL do serviço** (`https://vendas-cloud-xxxx.a.run.app`). Essa URL é o
sistema no ar. Abra `/` para o dashboard e `/docs` para a API.

`--allow-unauthenticated` torna a página pública (necessário para a banca acessar); o
**upload** continua protegido pela chave de API.

4. **Alerta de custo (R6):** Console > *Billing* > *Budgets & alerts* > criar orçamento de
   US$ 1 com alertas em 50% e 100%. Tirem print.

Se o deploy falhar com erro de permissão do Cloud Build, abra a mensagem de erro: ela indica
qual papel falta. Em geral basta conceder `roles/cloudbuild.builds.builder` à conta indicada.

Para atualizar depois de mudar o código: rode só o último `gcloud run deploy` de novo.

## 3. Roteiro de testes (Etapa 5) e evidências

Substituam `URL` e `CHAVE`. Tirem print de cada passo.

| # | Teste | Como | Resultado esperado |
|---|---|---|---|
| 1 | Acesso pela Internet | abrir `URL` num celular com 4G | dashboard carrega |
| 2 | Upload válido | `curl -H "X-API-Key: CHAVE" -F "arquivo=@dados_exemplo/vendas_exemplo.csv" URL/api/upload` | JSON com total R$ 3.295,00 e 48 itens |
| 3 | Dado gravado | Console > Cloud Storage > bucket | objeto `AAAAMMDDTHHMMSS_vendas_exemplo.csv` |
| 4 | Recuperação | `curl URL/api/arquivos` e `curl URL/api/relatorio` | lista e relatório consolidado |
| 5 | Processamento | dashboard: Meia Esportiva (18 un.) em 1º, Camiseta Básica (14 un.) em 2º | confere com o cálculo manual |
| 6 | Formato BR | enviar `vendas_formato_br.csv` | aceito (separador `;`, vírgula decimal) |
| 7 | Linhas ruins | enviar `vendas_com_erros.csv` | aceito, com 4 linhas rejeitadas listadas |
| 8 | Entrada inválida | enviar `vendas_cabecalho_invalido.csv` | HTTP 422 e nada é gravado no bucket |
| 9 | Sem chave | upload sem `X-API-Key` | HTTP 401 |
| 10 | Arquivo não CSV | enviar um `.txt` | HTTP 400 |
| 11 | Logs | Console > Cloud Run > Logs | requisições registradas |

Teste de acesso indevido ao bucket: abrir `https://storage.googleapis.com/SEU_BUCKET/arquivo.csv`
deve dar *Access denied* (bucket privado).

## 4. Dados e privacidade

Usem apenas dados fictícios (como em `dados_exemplo/`). O enunciado proíbe dados pessoais reais.

## 5. Custos

Dentro das cotas gratuitas mensais o custo esperado é **R$ 0**. Os limites "Always Free"
que encontrei publicados (confirmem na página oficial, pois o Google pode alterá-los): Cloud Run
com 2 milhões de requisições/mês e Cloud Storage com 5 GB, em regiões dos EUA como
`us-central1`, `us-east1` e `us-west1`. Para a estimativa do relatório, usem a
**Calculadora de Preços do Google Cloud** com o uso real do grupo.
