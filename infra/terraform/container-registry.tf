# ---------------------------------------------------------------------------
# Azure Container Registry
# ---------------------------------------------------------------------------

resource "azurerm_container_registry" "main" {
  name                = replace("${var.project_name}acr", "-", "")
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  sku                 = var.acr_sku
  admin_enabled       = true

  tags = local.common_tags
}
