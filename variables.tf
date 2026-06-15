variable "project_id" {
  type        = string
  description = "O ID do projeto no Google Cloud"
  default     = "toolkit-discovery-001"
}

variable "region" {
  type        = string
  description = "A região dos recursos"
  default     = "us-central1"
}

variable "app_name" {
  type        = string
  description = "O nome do serviço no Cloud Run"
  default     = "hub-observabilidade"
}

variable "artifact_registry_repo" {
  type        = string
  description = "O repositório de imagens Docker"
  default     = "hub-observabilidade"
}