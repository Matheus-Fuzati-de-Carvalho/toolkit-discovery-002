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
    }
  }
}