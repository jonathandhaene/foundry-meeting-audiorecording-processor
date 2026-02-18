# ---------------------------------------------------------------------------
# Storage Account
# ---------------------------------------------------------------------------

resource "azurerm_storage_account" "main" {
  name                          = replace("${var.project_name}stor", "-", "")
  resource_group_name           = data.azurerm_resource_group.main.name
  location                      = local.location
  account_tier                  = var.storage_account_tier
  account_replication_type      = var.storage_replication_type
  min_tls_version               = "TLS1_2"
  shared_access_key_enabled     = false

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Blob Containers
# ---------------------------------------------------------------------------

resource "azurerm_storage_container" "audio_files" {
  name                  = "meeting-audio-files"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "results" {
  name                  = "meeting-results"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}
