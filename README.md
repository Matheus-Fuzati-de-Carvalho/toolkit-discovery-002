# 📊 Hub de Observabilidade e Profiling de Dados (BigQuery)

Este projeto consiste em um **Hub de Observabilidade** conteinerizado, desenvolvido para atuar como uma plataforma central de inteligência, auditoria e análise estrutural de dados contidos no **Google BigQuery (BQ)**. 

O Hub foi desenhado para dar visibilidade completa sobre o ecossistema de dados, ajudando times de engenharia e governança a entender a saúde, o volume e a composição das tabelas corporativas.

---

## ⚙️ Como o Hub Funciona

O aplicativo opera realizando uma varredura analítica diretamente nas APIs do Google Cloud, estruturado em três camadas principais de funcionamento:

### 1. Conexão Nativa com o BigQuery
O Hub utiliza as bibliotecas oficiais do Google Cloud para se conectar de forma segura ao ambiente do BigQuery do projeto alvo. Ele herda as permissões da conta de execução para listar e interagir com os recursos de dados sem a necessidade de expor credenciais no código.

### 2. Catálogo e Informações Vitais de Tabelas
A aplicação varre os **Datasets** ativos e mapeia dinamicamente todas as tabelas existentes, extraindo e exibindo suas métricas vitais de infraestrutura em uma interface centralizada:
* Tamanho total da tabela em disco (Bytes/Gigabytes).
* Quantidade exata de linhas (*Row Count*).
* Data de criação e horário da última modificação/atualização dos dados.
* Tipo da tabela (Tabela nativa, Visão ou Tabela Externa).

### 3. Profiling Detalhado Coluna a Coluna ⚠️ *(Em Desenvolvimento)*
Uma camada avançada de qualidade de dados que realiza uma autópsia estatística na estrutura interna das tabelas. Quando finalizada, esta funcionalidade gerará um relatório detalhado analisando cada coluna individualmente:
* Identificação de tipos de dados e inferência de esquemas.
* Volumetria de valores nulos (*Null Share*) e preenchimento.
* Análise de cardinalidade (valores únicos) e detecção de possíveis chaves primárias.
* Distribuição estatística para campos numéricos e padrões de texto.

---

## 🛠️ Stack Tecnológica

* **Linguagem/Runtime:** Python (com bibliotecas `google-cloud-bigquery` e motores de análise estatística).
* **Containers:** Docker (Padronização do ambiente de execução).
* **Hospedagem:** Google Cloud Run (Infraestrutura serverless com auto-scaling).

---

## 🚀 Como é Feito o Deploy em um Novo Projeto

Para garantir que este Hub de Observabilidade seja agnóstico e possa ser implantado instantaneamente em qualquer novo projeto da empresa, todo o ciclo de vida da infraestrutura é controlado por uma esteira automatizada de **Terraform** e **GitHub Actions**.

O processo de deploy em um novo ambiente do GCP ocorre em poucos passos:

1. **Preparação no GCP:** O administrador do novo projeto ativa as APIs necessárias (`run`, `artifactregistry`, `bigquery`) e cria uma relação de confiança segura via **Workload Identity Federation (WIF)**, permitindo que o GitHub se conecte ao GCP sem chaves JSON fixas.
2. **Disparo Manual (Formulário):** Na aba *Actions* do GitHub, o operador aciona o fluxo informando apenas o ID do novo projeto, o número do projeto e a região desejada.
3. **Orquestração Automatizada:** * O **Terraform** entra em ação para criar o repositório seguro no *Artifact Registry*.
   * O **GitHub Actions** constrói a imagem Docker do Hub de Observabilidade e faz o `push` para esse repositório.
   * O **Terraform** finaliza o processo criando o serviço no *Cloud Run* apontando para a nova imagem e aplicando a política de IAM que libera o acesso público seguro à interface do Hub.
