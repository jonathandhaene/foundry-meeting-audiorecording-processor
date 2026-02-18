# ---------------------------------------------------------------------------
# Resource Group
# ---------------------------------------------------------------------------

output "resource_group_name" {
  description = "Name of the Azure resource group"
  value       = data.azurerm_resource_group.main.name
}

# ---------------------------------------------------------------------------
# Cognitive Services
# ---------------------------------------------------------------------------

output "speech_service_key" {
  description = "Primary key for Azure Speech Services"
  value       = azurerm_cognitive_account.speech.primary_access_key
  sensitive   = true
}

output "speech_service_region" {
  description = "Region of the Speech Services account"
  value       = azurerm_cognitive_account.speech.location
}

output "text_analytics_key" {
  description = "Primary key for Azure Text Analytics"
  value       = azurerm_cognitive_account.text_analytics.primary_access_key
  sensitive   = true
}

output "text_analytics_endpoint" {
  description = "Endpoint URL for Azure Text Analytics"
  value       = azurerm_cognitive_account.text_analytics.endpoint
}

output "openai_endpoint" {
  description = "Endpoint URL for Azure OpenAI (Whisper)"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "openai_whisper_deployment" {
  description = "Azure OpenAI Whisper deployment name"
  value       = azurerm_cognitive_deployment.whisper.name
}

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.main.name
}

# ---------------------------------------------------------------------------
# Container Registry
# ---------------------------------------------------------------------------

output "acr_login_server" {
  description = "Login server URL for Azure Container Registry"
  value       = azurerm_container_registry.main.login_server
}

output "acr_admin_username" {
  description = "Admin username for Azure Container Registry"
  value       = azurerm_container_registry.main.admin_username
}

output "acr_admin_password" {
  description = "Admin password for Azure Container Registry"
  value       = azurerm_container_registry.main.admin_password
  sensitive   = true
}

# ---------------------------------------------------------------------------
# App Service
# ---------------------------------------------------------------------------

output "backend_url" {
  description = "URL of the backend API"
  value       = "https://${azurerm_linux_web_app.backend.default_hostname}"
}

output "frontend_url" {
  description = "URL of the frontend UI"
  value       = "https://${azurerm_linux_web_app.frontend.default_hostname}"
}

# ---------------------------------------------------------------------------
# Function App
# ---------------------------------------------------------------------------

output "function_app_url" {
  description = "URL of the Function App (if deployed)"
  value       = var.deploy_function_app ? "https://${azurerm_linux_function_app.main[0].default_hostname}" : null
}

# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------

output "app_insights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true
}

output "app_insights_connection_string" {
  description = "Application Insights connection string"
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}
