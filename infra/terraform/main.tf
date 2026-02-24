# AutoForge — Production-Grade Terraform Configuration
# Multi-environment GCP deployment with full observability stack.

terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
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

provider "google-beta" {
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
  description = "Deployment environment (staging | production)"
  type        = string
  default     = "staging"
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be 'staging' or 'production'."
  }
}

variable "domain" {
  description = "Custom domain for the application"
  type        = string
  default     = ""
}

variable "anthropic_api_key" {
  description = "Anthropic API Key (stored in Secret Manager)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "gitlab_token" {
  description = "GitLab API token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "demo_mode" {
  description = "Enable demo mode (no real LLM calls)"
  type        = bool
  default     = true
}

locals {
  service_prefix = "autoforge-${var.environment}"
  labels = {
    project     = "autoforge"
    environment = var.environment
    managed_by  = "terraform"
  }
}

# ─── Enable Required APIs ──────────────────────────────

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
  ])

  project = var.project_id
  service = each.value

  disable_dependent_services = false
  disable_on_destroy         = false
}

# ─── Artifact Registry ────────────────────────────────

resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = "${local.service_prefix}-docker"
  format        = "DOCKER"
  labels        = local.labels

  depends_on = [google_project_service.apis]
}

# ─── Secret Manager ───────────────────────────────────

resource "google_secret_manager_secret" "anthropic_key" {
  secret_id = "${local.service_prefix}-anthropic-key"
  labels    = local.labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "anthropic_key" {
  secret      = google_secret_manager_secret.anthropic_key.id
  secret_data = var.anthropic_api_key
}

resource "google_secret_manager_secret" "gitlab_token" {
  secret_id = "${local.service_prefix}-gitlab-token"
  labels    = local.labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "gitlab_token" {
  secret      = google_secret_manager_secret.gitlab_token.id
  secret_data = var.gitlab_token
}

# ─── VPC Network ──────────────────────────────────────

resource "google_compute_network" "vpc" {
  name                    = "${local.service_prefix}-vpc"
  auto_create_subnetworks = false

  depends_on = [google_project_service.apis]
}

resource "google_compute_subnetwork" "subnet" {
  name          = "${local.service_prefix}-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id

  private_ip_google_access = true
}

resource "google_vpc_access_connector" "connector" {
  name          = "${local.service_prefix}-vpc"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.vpc.name
}

# ─── Cloud SQL: PostgreSQL ─────────────────────────────

resource "google_sql_database_instance" "postgres" {
  name             = "${local.service_prefix}-pg"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = var.environment == "production" ? "db-custom-2-8192" : "db-f1-micro"
    availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"

    disk_size    = var.environment == "production" ? 50 : 10
    disk_type    = "PD_SSD"

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }

    backup_configuration {
      enabled                        = var.environment == "production"
      point_in_time_recovery_enabled = var.environment == "production"
      start_time                     = "03:00"
    }

    database_flags {
      name  = "max_connections"
      value = var.environment == "production" ? "200" : "50"
    }

    user_labels = local.labels
  }

  deletion_protection = var.environment == "production"

  depends_on = [google_project_service.apis, google_compute_network.vpc]
}

resource "google_sql_database" "autoforge" {
  name     = "autoforge"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "autoforge" {
  name     = "autoforge"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
}

resource "random_password" "db_password" {
  length  = 32
  special = false
}

# ─── Memorystore: Redis ───────────────────────────────

resource "google_redis_instance" "redis" {
  name               = "${local.service_prefix}-redis"
  tier               = var.environment == "production" ? "STANDARD_HA" : "BASIC"
  memory_size_gb     = var.environment == "production" ? 2 : 1
  region             = var.region
  authorized_network = google_compute_network.vpc.id
  redis_version      = "REDIS_7_0"

  labels = local.labels

  depends_on = [google_project_service.apis]
}

# ─── Cloud Run: Backend API ────────────────────────────

resource "google_cloud_run_v2_service" "backend" {
  name     = "${local.service_prefix}-api"
  location = var.region
  labels   = local.labels

  template {
    service_account = google_service_account.backend.email

    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}/autoforge-backend:latest"

      ports {
        container_port = 8000
      }

      env {
        name  = "APP_ENV"
        value = var.environment
      }
      env {
        name  = "DEMO_MODE"
        value = tostring(var.demo_mode)
      }
      env {
        name  = "DATABASE_URL"
        value = "postgresql://autoforge:${random_password.db_password.result}@${google_sql_database_instance.postgres.private_ip_address}:5432/autoforge"
      }
      env {
        name  = "REDIS_URL"
        value = "redis://${google_redis_instance.redis.host}:${google_redis_instance.redis.port}/0"
      }
      env {
        name  = "LOG_LEVEL"
        value = var.environment == "production" ? "INFO" : "DEBUG"
      }
      env {
        name = "ANTHROPIC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.anthropic_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "GITLAB_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gitlab_token.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = var.environment == "production" ? "4" : "2"
          memory = var.environment == "production" ? "2Gi" : "1Gi"
        }
      }

      startup_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 5
        period_seconds        = 5
        failure_threshold     = 10
      }

      liveness_probe {
        http_get {
          path = "/health"
        }
        period_seconds    = 30
        failure_threshold = 3
      }
    }

    scaling {
      min_instance_count = var.environment == "production" ? 2 : 1
      max_instance_count = var.environment == "production" ? 10 : 5
    }
  }

  depends_on = [google_project_service.apis]
}

# ─── Cloud Run: Dashboard ─────────────────────────────

resource "google_cloud_run_v2_service" "dashboard" {
  name     = "${local.service_prefix}-dashboard"
  location = var.region
  labels   = local.labels

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}/autoforge-dashboard:latest"

      ports {
        container_port = 3000
      }

      env {
        name  = "NEXT_PUBLIC_API_URL"
        value = google_cloud_run_v2_service.backend.uri
      }
      env {
        name  = "NEXT_PUBLIC_WS_URL"
        value = replace(google_cloud_run_v2_service.backend.uri, "https://", "wss://")
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
      max_instance_count = var.environment == "production" ? 5 : 3
    }
  }

  depends_on = [google_project_service.apis]
}

# ─── IAM: Service Accounts ────────────────────────────

resource "google_service_account" "backend" {
  account_id   = "${local.service_prefix}-api"
  display_name = "AutoForge Backend Service Account"
}

resource "google_secret_manager_secret_iam_member" "backend_anthropic" {
  secret_id = google_secret_manager_secret.anthropic_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_secret_manager_secret_iam_member" "backend_gitlab" {
  secret_id = google_secret_manager_secret.gitlab_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

# ─── Public Access (allow unauthenticated) ────────────

resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  name     = google_cloud_run_v2_service.backend.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "dashboard_public" {
  name     = google_cloud_run_v2_service.dashboard.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ─── Monitoring: Uptime Checks ────────────────────────

resource "google_monitoring_uptime_check_config" "backend_health" {
  display_name = "${local.service_prefix}-health"
  timeout      = "10s"
  period       = "60s"

  http_check {
    path         = "/health"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = replace(google_cloud_run_v2_service.backend.uri, "https://", "")
    }
  }
}

# ─── Outputs ──────────────────────────────────────────

output "backend_url" {
  description = "Backend API URL"
  value       = google_cloud_run_v2_service.backend.uri
}

output "dashboard_url" {
  description = "Dashboard URL"
  value       = google_cloud_run_v2_service.dashboard.uri
}

output "postgres_connection" {
  description = "PostgreSQL private IP"
  value       = google_sql_database_instance.postgres.private_ip_address
  sensitive   = true
}

output "redis_host" {
  description = "Redis host"
  value       = google_redis_instance.redis.host
}

output "artifact_registry" {
  description = "Docker image registry"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}
