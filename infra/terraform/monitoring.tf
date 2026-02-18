# ---------------------------------------------------------------------------
# Log Analytics Workspace
# ---------------------------------------------------------------------------

resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.project_name}-logs"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Application Insights
# ---------------------------------------------------------------------------

resource "azurerm_application_insights" "main" {
  name                = "${var.project_name}-insights"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"

  tags = local.common_tags
}
