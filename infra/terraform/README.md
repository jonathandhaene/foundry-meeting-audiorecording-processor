# Terraform – Azure Infrastructure

This directory contains Terraform configuration to provision all Azure resources required by the Meeting Audio Recording Processor.

## Resources Created

| Resource | Terraform file | Purpose |
|---|---|---|
| Resource Group | `main.tf` | Container for all resources |
| Speech Services | `cognitive-services.tf` | Audio transcription |
| Text Analytics | `cognitive-services.tf` | NLP analysis (sentiment, key phrases, etc.) |
| Storage Account + Containers | `storage.tf` | Audio file and results storage |
| Container Registry (ACR) | `container-registry.tf` | Docker image hosting |
| App Service Plan | `app-service.tf` | Hosting plan for backend & frontend |
| Backend Web App | `app-service.tf` | FastAPI backend (Docker) |
| Frontend Web App | `app-service.tf` | React frontend (Docker) |
| Function App *(optional)* | `function-app.tf` | Serverless audio processing |
| Log Analytics Workspace | `monitoring.tf` | Log aggregation |
| Application Insights | `monitoring.tf` | Performance monitoring & telemetry |

## Prerequisites

- [Terraform >= 1.5](https://developer.hashicorp.com/terraform/install)
- [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli)
- An active Azure subscription

## Quick Start

```bash
# 1. Authenticate with Azure
az login

# 2. Navigate to this directory
cd infra/terraform

# 3. Create your variables file
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars – at minimum set subscription_id

# 4. Initialise Terraform
terraform init

# 5. Preview the changes
terraform plan

# 6. Apply
terraform apply
```

## After Deployment

### Push Docker images to ACR

```bash
# Get ACR login server from Terraform output
ACR_SERVER=$(terraform output -raw acr_login_server)

# Log in to ACR
az acr login --name $(terraform output -raw acr_login_server | cut -d. -f1)

# Build & push backend
docker build -t $ACR_SERVER/meeting-processor:latest ../../
docker push $ACR_SERVER/meeting-processor:latest

# Build & push frontend
docker build -t $ACR_SERVER/meeting-processor-ui:latest ../../frontend/
docker push $ACR_SERVER/meeting-processor-ui:latest
```

### Retrieve sensitive outputs

```bash
terraform output -raw speech_service_key
terraform output -raw text_analytics_key
terraform output -raw storage_connection_string
```

### Deploy Function App code

```bash
cd ../../azure_functions
func azure functionapp publish $(terraform -chdir=../infra/terraform output -raw function_app_url | sed 's|https://||;s|\.azurewebsites\.net||')
```

## Configuration

All configurable variables are in `variables.tf`. See `terraform.tfvars.example` for a documented template. Key settings:

| Variable | Default | Description |
|---|---|---|
| `subscription_id` | *(required)* | Your Azure subscription ID |
| `project_name` | `meeting-processor` | Prefix for all resource names |
| `location` | `eastus` | Azure region |
| `environment` | `dev` | `dev`, `staging`, or `prod` |
| `deploy_function_app` | `true` | Set `false` to skip Function App |
| `app_service_sku` | `B1` | App Service plan size |
| `openai_api_key` | `""` | Optional – for Whisper transcription |

## Remote State (recommended for teams)

Uncomment the `backend "azurerm"` block in `main.tf` and create the storage resources:

```bash
az group create -n terraform-state-rg -l eastus
az storage account create -n tfstatemeetingproc -g terraform-state-rg -l eastus --sku Standard_LRS
az storage container create -n tfstate --account-name tfstatemeetingproc
```

Then run `terraform init` again to migrate state.

## Tear Down

```bash
terraform destroy
```
