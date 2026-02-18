# ---------------------------------------------------------------------------
# App Service Plan (shared by backend and frontend)
# ---------------------------------------------------------------------------

resource "azurerm_service_plan" "main" {
  name                = "${var.project_name}-plan"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  os_type             = "Linux"
  sku_name            = var.app_service_sku

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Backend – Linux Web App (Docker container)
# ---------------------------------------------------------------------------

resource "azurerm_linux_web_app" "backend" {
  name                = "${var.project_name}-api"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  service_plan_id     = azurerm_service_plan.main.id

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      docker_registry_url      = "https://${azurerm_container_registry.main.login_server}"
      docker_registry_username = azurerm_container_registry.main.admin_username
      docker_registry_password = azurerm_container_registry.main.admin_password
      docker_image_name        = "meeting-processor-api:${var.docker_image_tag}"
    }

    always_on = var.app_service_sku != "F1" # Free tier doesn't support always-on
  }

  app_settings = {
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE" = "true"
    "WEBSITES_PORT"                       = "8000"

    # Azure Cognitive Services
    "AZURE_SPEECH_REGION"            = local.location
    "AZURE_SPEECH_RESOURCE_ID"       = azurerm_cognitive_account.speech.id
    "AZURE_SPEECH_ENDPOINT"          = azurerm_cognitive_account.speech.endpoint
    "AZURE_TEXT_ANALYTICS_ENDPOINT"  = azurerm_cognitive_account.text_analytics.endpoint

    # Azure OpenAI (Whisper)
    "AZURE_OPENAI_ENDPOINT"         = azurerm_cognitive_account.openai.endpoint
    "AZURE_OPENAI_WHISPER_DEPLOYMENT" = azurerm_cognitive_deployment.whisper.name

    # Storage
    "AZURE_STORAGE_ACCOUNT_NAME"  = azurerm_storage_account.main.name
    "AZURE_STORAGE_CONTAINER_NAME" = azurerm_storage_container.audio_files.name

    # App configuration
    "DEFAULT_LANGUAGE"             = var.default_language
    "ENABLE_SPEAKER_DIARIZATION"   = tostring(var.enable_speaker_diarization)
    "MAX_SPEAKERS"                 = tostring(var.max_speakers)
    "OPENAI_API_KEY"               = var.openai_api_key

    # Monitoring
    "APPINSIGHTS_INSTRUMENTATIONKEY"        = azurerm_application_insights.main.instrumentation_key
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.main.connection_string

    # Binding
    "API_HOST" = "0.0.0.0"
    "API_PORT" = "8000"
  }

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Frontend – Linux Web App (Docker container from frontend/)
# ---------------------------------------------------------------------------

resource "azurerm_linux_web_app" "frontend" {
  name                = "${var.project_name}-ui"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  service_plan_id     = azurerm_service_plan.main.id

  site_config {
    application_stack {
      docker_registry_url      = "https://${azurerm_container_registry.main.login_server}"
      docker_registry_username = azurerm_container_registry.main.admin_username
      docker_registry_password = azurerm_container_registry.main.admin_password
      docker_image_name        = "meeting-processor-ui:${var.docker_image_tag}"
    }

    always_on = var.app_service_sku != "F1"
  }

  app_settings = {
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE" = "false"
    "REACT_APP_API_URL"                   = "https://${azurerm_linux_web_app.backend.default_hostname}"
    "API_BACKEND"                         = azurerm_linux_web_app.backend.default_hostname
  }

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Role Assignment – Backend managed identity -> Main Storage
# ---------------------------------------------------------------------------

resource "azurerm_role_assignment" "backend_storage_blob" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_linux_web_app.backend.identity[0].principal_id
}

# ---------------------------------------------------------------------------
# Role Assignments – Backend managed identity -> Cognitive Services
# ---------------------------------------------------------------------------

resource "azurerm_role_assignment" "backend_speech" {
  scope                = azurerm_cognitive_account.speech.id
  role_definition_name = "Cognitive Services Speech User"
  principal_id         = azurerm_linux_web_app.backend.identity[0].principal_id
}

resource "azurerm_role_assignment" "backend_speech_contributor" {
  scope                = azurerm_cognitive_account.speech.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_linux_web_app.backend.identity[0].principal_id
}

resource "azurerm_role_assignment" "backend_text_analytics" {
  scope                = azurerm_cognitive_account.text_analytics.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_linux_web_app.backend.identity[0].principal_id
}

resource "azurerm_role_assignment" "backend_openai" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_linux_web_app.backend.identity[0].principal_id
}
