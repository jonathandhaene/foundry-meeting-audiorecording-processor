# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------

variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "project_name" {
  description = "Project name used as a prefix for all resources"
  type        = string
  default     = "meeting-processor"
}

variable "resource_group_name" {
  description = "Name of an existing Azure Resource Group to deploy into"
  type        = string
}

variable "location" {
  description = "Azure region for all resources (defaults to the resource group's location)"
  type        = string
  default     = ""
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# ---------------------------------------------------------------------------
# Cognitive Services
# ---------------------------------------------------------------------------

variable "speech_services_sku" {
  description = "SKU for Azure Speech Services (F0 = free, S0 = standard)"
  type        = string
  default     = "S0"
}

variable "text_analytics_sku" {
  description = "SKU for Azure Text Analytics (F0 = free, S = standard)"
  type        = string
  default     = "S"
}

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

variable "storage_account_tier" {
  description = "Storage account tier"
  type        = string
  default     = "Standard"
}

variable "storage_replication_type" {
  description = "Storage account replication type"
  type        = string
  default     = "LRS"
}

# ---------------------------------------------------------------------------
# Container Registry
# ---------------------------------------------------------------------------

variable "acr_sku" {
  description = "SKU for Azure Container Registry (Basic, Standard, Premium)"
  type        = string
  default     = "Basic"
}

# ---------------------------------------------------------------------------
# App Service
# ---------------------------------------------------------------------------

variable "app_service_sku" {
  description = "SKU for Azure App Service Plan"
  type        = string
  default     = "B1"
}

variable "docker_image_tag" {
  description = "Docker image tag for the backend container"
  type        = string
  default     = "latest"
}

# ---------------------------------------------------------------------------
# Function App
# ---------------------------------------------------------------------------

variable "deploy_function_app" {
  description = "Whether to deploy the Azure Function App for serverless processing"
  type        = bool
  default     = true
}

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------

variable "default_language" {
  description = "Default language for transcription (e.g., en-US)"
  type        = string
  default     = "en-US"
}

variable "enable_speaker_diarization" {
  description = "Enable speaker diarization in transcription"
  type        = bool
  default     = true
}

variable "max_speakers" {
  description = "Maximum number of speakers for diarization"
  type        = number
  default     = 10
}

variable "openai_api_key" {
  description = "OpenAI API key (for Whisper transcription)"
  type        = string
  default     = ""
  sensitive   = true
}
