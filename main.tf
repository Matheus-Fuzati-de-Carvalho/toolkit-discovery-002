terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 📦 Cria o repositório no Artifact Registry
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = var.artifact_registry_repo
  description   = "Repositorio Docker do Hub"
  format        = "DOCKER"
}

# ☁️ Cria o serviço no Cloud Run apontando para a imagem real
resource "google_cloud_run_v2_service" "app" {
  name     = var.app_name
  location = var.region

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}/${var.app_name}:latest"
      
      ports {
        container_port = 8080
      }
      env {
        name  = "GIT_SHA"
        value = var.git_sha
      }
    }
  }
}

# 1. Declare a nova variável no seu main.tf
variable "git_sha" {
  type        = string
  description = "Hash do commit para forçar o deploy"
  default     = "local"
}

# 🔓 Libera o acesso público (não autenticado) para qualquer pessoa na internet
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}