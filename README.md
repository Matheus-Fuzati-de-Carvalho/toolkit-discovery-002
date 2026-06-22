# 📊 Hub de Observabilidade e Profiling de Dados (BigQuery)

Plataforma desenvolvida para o **Google Cloud Run** com foco em **FinOps, governança e qualidade de dados**. O Hub atua como uma camada central para monitorar a saúde, a volumetria e os custos ocultos do Google BigQuery (BQ), utilizando metadados nativos com custo zero e algoritmos probabilísticos avançados.

---

## ⚙️ Funcionalidades Principais

* **Catálogo Dinâmico (Custo Zero):** Autodescoberta de datasets, tabelas (nativas/externas) e views. Exibe a região geográfica, tamanho em disco (Bytes/TB), contagem exata de linhas e monitoramento de *Freshness* (SLAs de atualização em janelas de 12h, 24h, 48h ou obsoletas).
* **Profiling Avançado (FinOps Guard):** Análise estatística coluna a coluna para validar preenchimento (*Null Share*) e cardinalidade (valores únicos). Conta com o mecanismo de *Dry Run*, que calcula os bytes escaneados e o custo estimado em USD antes da execução da consulta, além de suporte a amostragem (*TABLESAMPLE*) e filtros temporais.
* **Interseção Probabilística (HLL):** Identifica a sobreposição de registros comuns entre tabelas massivas utilizando algoritmos *HyperLogLog* (`HLL_COUNT.INIT` e `HLL_COUNT.MERGE`). Substitui `INNER JOINs` pesados por um processamento leve em memória, reduzindo o custo computacional e financeiro a quase zero.

---

## 🛠️ Stack Tecnológica

* **Backend / API:** Python 3.11, FastAPI, Uvicorn, Pandas e Google Cloud BigQuery Client Core.
* **Frontend:** Vue.js 3 e TailwindCSS (Arquitetura de Componentes).
* **Infraestrutura:** Docker, Terraform e GitHub Actions (Esteira de CI/CD).

---

## 📋 Pré-requisitos para o Time de TI (GCP)

Solicite à equipe de infraestrutura e segurança do Google Cloud Platform as seguintes configurações no projeto alvo:

1.  **Ativação de APIs Nativas:**
    * `run.googleapis.com` (Cloud Run)
    * `artifactregistry.googleapis.com` (Artifact Registry)
    * `bigquery.googleapis.com` (BigQuery Engine)
    * `iam.googleapis.com` (Identity and Access Management)
2.  **Autenticação via Workload Identity Federation (WIF):** Criação de um pool de identidade vinculado ao repositório do GitHub para permitir deploys automáticos e seguros, eliminando o uso de chaves JSON privadas.
3.  **Permissões da Service Account de Execução (Runtime IAM):**
    * `roles/bigquery.metadataViewer` (Leitura gratuita do catálogo de metadados).
    * `roles/bigquery.user` (Permissão para executar Jobs e consultas de profiling/HLL).
    * `roles/bigquery.dataViewer` (Visualização de schemas e amostras estatísticas).

---

## 🚀 Passo a Passo para o Deploy

### Passo 1: Ajustar Variáveis de Infraestrutura

Abra o arquivo `toolkit-discovery-002/variables.tf` no seu ambiente de desenvolvimento e configure os valores padrão com os dados fornecidos pelo time de TI:
  
    variable "project_id" {
    type        = string
    description = "O ID do projeto alvo no Google Cloud fornecido pela TI"
    default     = "seu-projeto-gcp-aqui"
    }
  
    variable "region" {
    type        = string
    description = "A região onde a infraestrutura será criada"
    default     = "us-central1"
    }


Passo 2: Executar via GitHub Actions (Esteira Automatizada)
Vá até o repositório do projeto no GitHub.

 * Acesse a aba Actions e selecione o workflow Deploy Hub Observabilidade.

  * Clique no botão Run workflow, insira o ID do projeto GCP correspondente e confirme o disparo.

  💡 O que a automação fará: O Terraform provisionará o repositório privado no Artifact Registry, compilará a imagem Docker da aplicação, realizará o push e publicará o serviço escalável no Cloud Run com uma URL pública protegida por certificado SSL automático da Google.
