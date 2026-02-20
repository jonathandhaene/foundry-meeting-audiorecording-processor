# ---------------------------------------------------------------------------
# HuggingFace Wav2Vec 2.0 Inference Server – Microsoft Foundry Pipeline
#
# This file provisions the Azure resources required to host a HuggingFace
# Wav2Vec 2.0 inference server via Azure Machine Learning (Foundry).
#
# Resources created:
#   - Azure Machine Learning workspace (Foundry)
#   - AML managed online endpoint for Wav2Vec 2.0 inference
#   - Application Insights instance (diagnostics)
#   - Key Vault entry for the HuggingFace API token
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Variables specific to the HuggingFace Inference pipeline
# ---------------------------------------------------------------------------

variable "hf_deploy_inference_server" {
  description = "Whether to deploy the HuggingFace Wav2Vec 2.0 inference server"
  type        = bool
  default     = false
}

variable "hf_wav2vec_model_name" {
  description = "HuggingFace model identifier to deploy (e.g., facebook/wav2vec2-base-960h)"
  type        = string
  default     = "facebook/wav2vec2-base-960h"
}

variable "hf_inference_instance_type" {
  description = "Azure ML compute instance type for the inference endpoint"
  type        = string
  default     = "Standard_DS3_v2"
}

variable "hf_inference_instance_count" {
  description = "Number of instances for the inference endpoint"
  type        = number
  default     = 1

  validation {
    condition     = var.hf_inference_instance_count >= 1 && var.hf_inference_instance_count <= 10
    error_message = "Instance count must be between 1 and 10."
  }
}

variable "hf_api_token" {
  description = "HuggingFace API token (stored in Key Vault). Required for private models."
  type        = string
  default     = ""
  sensitive   = true
}

# ---------------------------------------------------------------------------
# Azure Machine Learning Workspace (Microsoft Foundry)
# ---------------------------------------------------------------------------

resource "azurerm_machine_learning_workspace" "hf_foundry" {
  count = var.hf_deploy_inference_server ? 1 : 0

  name                    = "${var.project_name}-hf-foundry-${var.environment}"
  location                = local.location
  resource_group_name     = data.azurerm_resource_group.main.name
  application_insights_id = azurerm_application_insights.hf_insights[0].id
  key_vault_id            = azurerm_key_vault.hf_kv[0].id
  storage_account_id      = azurerm_storage_account.main.id

  identity {
    type = "SystemAssigned"
  }

  tags = local.common_tags

  lifecycle {
    ignore_changes = [storage_account_id]
  }
}

# ---------------------------------------------------------------------------
# Application Insights for the Foundry workspace
# ---------------------------------------------------------------------------

resource "azurerm_application_insights" "hf_insights" {
  count = var.hf_deploy_inference_server ? 1 : 0

  name                = "${var.project_name}-hf-insights-${var.environment}"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  application_type    = "web"

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Key Vault for HuggingFace secrets
# ---------------------------------------------------------------------------

data "azurerm_client_config" "current" {}

locals {
  # Azure Key Vault names must be 3-24 chars and globally unique.
  # Truncate to stay within the 24-character limit.
  hf_kv_name = substr("${var.project_name}-hf-kv-${var.environment}", 0, 24)
}

resource "azurerm_key_vault" "hf_kv" {
  count = var.hf_deploy_inference_server ? 1 : 0

  name                = local.hf_kv_name
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  purge_protection_enabled   = false
  soft_delete_retention_days = 7
  enable_rbac_authorization  = true

  tags = local.common_tags
}

# Store HuggingFace API token in Key Vault (only when token is provided)
resource "azurerm_key_vault_secret" "hf_api_token" {
  count = var.hf_deploy_inference_server && var.hf_api_token != "" ? 1 : 0

  name         = "huggingface-api-token"
  value        = var.hf_api_token
  key_vault_id = azurerm_key_vault.hf_kv[0].id

  depends_on = [azurerm_key_vault.hf_kv]
}

# ---------------------------------------------------------------------------
# RBAC: allow the AML workspace identity to read Key Vault secrets
# ---------------------------------------------------------------------------

resource "azurerm_role_assignment" "aml_kv_reader" {
  count = var.hf_deploy_inference_server ? 1 : 0

  scope                = azurerm_key_vault.hf_kv[0].id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_machine_learning_workspace.hf_foundry[0].identity[0].principal_id

  depends_on = [
    azurerm_machine_learning_workspace.hf_foundry,
    azurerm_key_vault.hf_kv,
  ]
}

# ---------------------------------------------------------------------------
# Azure ML Managed Online Endpoint for Wav2Vec 2.0 inference
#
# The endpoint exposes a REST API that the HuggingFaceTranscriber can call
# by setting: hf_endpoint = azurerm_machine_learning_online_endpoint.wav2vec[0].scoring_uri
# ---------------------------------------------------------------------------

resource "azurerm_machine_learning_online_endpoint" "wav2vec" {
  count = var.hf_deploy_inference_server ? 1 : 0

  name                          = "${var.project_name}-wav2vec-${var.environment}"
  location                      = local.location
  resource_group_name           = data.azurerm_resource_group.main.name
  machine_learning_workspace_id = azurerm_machine_learning_workspace.hf_foundry[0].id
  auth_mode                     = "key"

  identity {
    type = "SystemAssigned"
  }

  tags = merge(local.common_tags, {
    hf_model = var.hf_wav2vec_model_name
  })

  depends_on = [azurerm_machine_learning_workspace.hf_foundry]
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "hf_foundry_workspace_id" {
  description = "Resource ID of the Azure ML (Foundry) workspace for HuggingFace inference"
  value       = var.hf_deploy_inference_server ? azurerm_machine_learning_workspace.hf_foundry[0].id : null
}

output "hf_inference_endpoint_uri" {
  description = "Scoring URI for the Wav2Vec 2.0 managed online endpoint. Set as HUGGINGFACE_ENDPOINT_URL."
  value       = var.hf_deploy_inference_server ? azurerm_machine_learning_online_endpoint.wav2vec[0].scoring_uri : null
}

output "hf_key_vault_id" {
  description = "Resource ID of the Key Vault used for HuggingFace secrets"
  value       = var.hf_deploy_inference_server ? azurerm_key_vault.hf_kv[0].id : null
}
