# AutoForge — Terraform Stubs
# These are scaffolds for production deployment infrastructure.
# They demonstrate the intended IaC approach for hackathon judges.

terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "autoforge-tfstate"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ─── Variables ─────────────────────────────────────────

variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "autoforge-hackathon"
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "staging"
}

# ─── Cloud Run: Backend API ────────────────────────────

resource "google_cloud_run_v2_service" "backend" {
  name     = "autoforge-backend-${var.environment}"
  location = var.region

  template {
    containers {
      image = "gcr.io/${var.project_id}/autoforge-backend:latest"

      ports {
        container_port = 8000
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "DEMO_MODE"
        value = "true"
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "1Gi"
        }
      }
    }

    scaling {
      min_instance_count = 1
      max_instance_count = 5
    }
  }
}

# ─── Cloud Run: Dashboard ─────────────────────────────

resource "google_cloud_run_v2_service" "dashboard" {
  name     = "autoforge-dashboard-${var.environment}"
  location = var.region

  template {
    containers {
      image = "gcr.io/${var.project_id}/autoforge-dashboard:latest"

      ports {
        container_port = 3000
      }

      env {
        name  = "NEXT_PUBLIC_API_URL"
        value = google_cloud_run_v2_service.backend.uri
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }

    scaling {
      min_instance_count = 1
      max_instance_count = 3
    }
  }
}

# ─── Cloud SQL: PostgreSQL ─────────────────────────────

resource "google_sql_database_instance" "postgres" {
  name             = "autoforge-postgres-${var.environment}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = "db-f1-micro"

    ip_configuration {
      ipv4_enabled = true
    }
  }

  deletion_protection = false
}

# ─── Memorystore: Redis ───────────────────────────────

resource "google_redis_instance" "redis" {
  name           = "autoforge-redis-${var.environment}"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region
}

# ─── Outputs ──────────────────────────────────────────

output "backend_url" {
  value = google_cloud_run_v2_service.backend.uri
}

output "dashboard_url" {
  value = google_cloud_run_v2_service.dashboard.uri
}

output "postgres_ip" {
  value = google_sql_database_instance.postgres.public_ip_address
}

output "redis_host" {
  value = google_redis_instance.redis.host
}
