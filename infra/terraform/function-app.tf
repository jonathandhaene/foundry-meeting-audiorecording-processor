# ---------------------------------------------------------------------------
# Function App – Serverless audio processing (optional)
# ---------------------------------------------------------------------------

# Dedicated storage account for the Function App runtime
resource "azurerm_storage_account" "functions" {
  count = var.deploy_function_app ? 1 : 0

  name                          = replace("${var.project_name}func", "-", "")
  resource_group_name           = data.azurerm_resource_group.main.name
  location                      = local.location
  account_tier                  = "Standard"
  account_replication_type      = "LRS"
  min_tls_version               = "TLS1_2"
  shared_access_key_enabled     = false

  tags = local.common_tags
}

# Consumption plan for Function App
resource "azurerm_service_plan" "functions" {
  count = var.deploy_function_app ? 1 : 0

  name                = "${var.project_name}-func-plan"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  os_type             = "Linux"
  sku_name            = "Y1" # Consumption plan

  tags = local.common_tags
}

resource "azurerm_linux_function_app" "main" {
  count = var.deploy_function_app ? 1 : 0

  name                       = "${var.project_name}-func"
  resource_group_name        = data.azurerm_resource_group.main.name
  location                   = local.location
  service_plan_id            = azurerm_service_plan.functions[0].id
  storage_account_name       = azurerm_storage_account.functions[0].name
  storage_uses_managed_identity = true

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.11"
    }
  }

  app_settings = {
    # Azure Cognitive Services
    "AZURE_SPEECH_KEY"              = azurerm_cognitive_account.speech.primary_access_key
    "AZURE_SPEECH_REGION"           = local.location
    "AZURE_SPEECH_ENDPOINT"         = azurerm_cognitive_account.speech.endpoint
    "AZURE_TEXT_ANALYTICS_KEY"      = azurerm_cognitive_account.text_analytics.primary_access_key
    "AZURE_TEXT_ANALYTICS_ENDPOINT" = azurerm_cognitive_account.text_analytics.endpoint

    # Storage (main storage account for audio/results)
    "AZURE_STORAGE_ACCOUNT_NAME"  = azurerm_storage_account.main.name
    "AZURE_STORAGE_CONTAINER_NAME" = azurerm_storage_container.audio_files.name

    # App configuration
    "DEFAULT_LANGUAGE"           = var.default_language
    "ENABLE_SPEAKER_DIARIZATION" = tostring(var.enable_speaker_diarization)
    "MAX_SPEAKERS"               = tostring(var.max_speakers)
    "OPENAI_API_KEY"             = var.openai_api_key

    # Monitoring
    "APPINSIGHTS_INSTRUMENTATIONKEY"        = azurerm_application_insights.main.instrumentation_key
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.main.connection_string

    # Python worker
    "AzureWebJobsFeatureFlags"       = "EnableWorkerIndexing"
    "BUILD_FLAGS"                    = "UseExpressBuild"
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
  }

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Role Assignments – Function App managed identity -> Storage
# ---------------------------------------------------------------------------

# Function App needs Blob Data Contributor on its own storage account
resource "azurerm_role_assignment" "func_storage_blob" {
  count = var.deploy_function_app ? 1 : 0

  scope                = azurerm_storage_account.functions[0].id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_linux_function_app.main[0].identity[0].principal_id
}

resource "azurerm_role_assignment" "func_storage_queue" {
  count = var.deploy_function_app ? 1 : 0

  scope                = azurerm_storage_account.functions[0].id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = azurerm_linux_function_app.main[0].identity[0].principal_id
}

resource "azurerm_role_assignment" "func_storage_table" {
  count = var.deploy_function_app ? 1 : 0

  scope                = azurerm_storage_account.functions[0].id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_linux_function_app.main[0].identity[0].principal_id
}

# Function App also needs access to the main storage account (audio files)
resource "azurerm_role_assignment" "func_main_storage_blob" {
  count = var.deploy_function_app ? 1 : 0

  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_linux_function_app.main[0].identity[0].principal_id
}
