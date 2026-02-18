terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  # Uncomment and configure for remote state storage
  # backend "azurerm" {
  #   resource_group_name  = "terraform-state-rg"
  #   storage_account_name = "tfstatemeetingproc"
  #   container_name       = "tfstate"
  #   key                  = "meeting-processor.tfstate"
  # }
}

provider "azurerm" {
  features {
    cognitive_account {
      purge_soft_delete_on_destroy = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }

  subscription_id      = var.subscription_id
  storage_use_azuread  = true
}

# ---------------------------------------------------------------------------
# Resource Group (existing – looked up via data source)
# ---------------------------------------------------------------------------

data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}

# ---------------------------------------------------------------------------
# Locals
# ---------------------------------------------------------------------------

locals {
  # Use explicit location if provided, otherwise inherit from the existing resource group
  location = var.location != "" ? var.location : data.azurerm_resource_group.main.location

  common_tags = merge(var.tags, {
    project     = var.project_name
    environment = var.environment
    managed_by  = "terraform"
  })
}
