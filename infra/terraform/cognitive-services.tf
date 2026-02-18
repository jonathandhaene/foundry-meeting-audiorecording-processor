# ---------------------------------------------------------------------------
# Azure Cognitive Services – Speech Services
# ---------------------------------------------------------------------------

resource "azurerm_cognitive_account" "speech" {
  name                  = "${var.project_name}-speech"
  resource_group_name   = data.azurerm_resource_group.main.name
  location              = local.location
  kind                  = "SpeechServices"
  sku_name              = var.speech_services_sku
  local_auth_enabled    = true
  custom_subdomain_name = "${var.project_name}-speech"

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Azure Cognitive Services – Text Analytics (Language)
# ---------------------------------------------------------------------------

resource "azurerm_cognitive_account" "text_analytics" {
  name                = "${var.project_name}-text-analytics"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  kind                = "TextAnalytics"
  sku_name            = var.text_analytics_sku
  local_auth_enabled  = true

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Azure OpenAI – for Whisper transcription
# ---------------------------------------------------------------------------

resource "azurerm_cognitive_account" "openai" {
  name                  = "${var.project_name}-openai"
  resource_group_name   = data.azurerm_resource_group.main.name
  location              = local.location
  kind                  = "OpenAI"
  sku_name              = "S0"
  local_auth_enabled    = true
  custom_subdomain_name = "${var.project_name}-openai"

  tags = local.common_tags
}

resource "azurerm_cognitive_deployment" "whisper" {
  name                 = "whisper"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "whisper"
    version = "001"
  }

  sku {
    name     = "Standard"
    capacity = 1
  }
}
