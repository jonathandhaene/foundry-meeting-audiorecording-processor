# Azure Setup Guide

This guide will walk you through setting up Azure services required for the Meeting Audio Recording Processor.

## Prerequisites

- Active Azure subscription
- Azure CLI installed ([Installation guide](https://docs.microsoft.com/cli/azure/install-azure-cli))
- Appropriate permissions to create resources in Azure

## Step 1: Login to Azure

```bash
az login
```

## Step 2: Create a Resource Group

```bash
az group create \
  --name meeting-processor-rg \
  --location eastus
```

## Step 3: Create Azure Speech Services

```bash
az cognitiveservices account create \
  --name meeting-speech-service \
  --resource-group meeting-processor-rg \
  --kind SpeechServices \
  --sku S0 \
  --location eastus \
  --yes
```

Get the API key:

```bash
az cognitiveservices account keys list \
  --name meeting-speech-service \
  --resource-group meeting-processor-rg
```

## Step 4: Create Azure Text Analytics

```bash
az cognitiveservices account create \
  --name meeting-text-analytics \
  --resource-group meeting-processor-rg \
  --kind TextAnalytics \
  --sku S \
  --location eastus \
  --yes
```

Get the API key and endpoint:

```bash
# Get keys
az cognitiveservices account keys list \
  --name meeting-text-analytics \
  --resource-group meeting-processor-rg

# Get endpoint
az cognitiveservices account show \
  --name meeting-text-analytics \
  --resource-group meeting-processor-rg \
  --query properties.endpoint \
  --output tsv
```

## Step 5: Create Azure Storage Account (Optional)

For Azure Functions and file storage:

```bash
az storage account create \
  --name meetingprocessorstorage \
  --resource-group meeting-processor-rg \
  --location eastus \
  --sku Standard_LRS
```

Get the connection string:

```bash
az storage account show-connection-string \
  --name meetingprocessorstorage \
  --resource-group meeting-processor-rg \
  --output tsv
```

Create storage containers:

```bash
# Get storage account key
STORAGE_KEY=$(az storage account keys list \
  --account-name meetingprocessorstorage \
  --resource-group meeting-processor-rg \
  --query '[0].value' -o tsv)

# Create containers
az storage container create \
  --name meeting-audio-files \
  --account-name meetingprocessorstorage \
  --account-key $STORAGE_KEY

az storage container create \
  --name meeting-results \
  --account-name meetingprocessorstorage \
  --account-key $STORAGE_KEY
```

## Step 6: Create Azure Functions App (Optional)

For serverless deployment:

```bash
az functionapp create \
  --resource-group meeting-processor-rg \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --name meeting-processor-func \
  --storage-account meetingprocessorstorage
```

Configure application settings:

```bash
az functionapp config appsettings set \
  --name meeting-processor-func \
  --resource-group meeting-processor-rg \
  --settings \
    AZURE_SPEECH_KEY="<your-speech-key>" \
    AZURE_SPEECH_REGION="eastus" \
    AZURE_TEXT_ANALYTICS_KEY="<your-text-analytics-key>" \
    AZURE_TEXT_ANALYTICS_ENDPOINT="<your-endpoint>" \
    DEFAULT_LANGUAGE="en-US" \
    ENABLE_SPEAKER_DIARIZATION="true" \
    MAX_SPEAKERS="10"
```

## Step 7: Configure Local Environment

Create a `.env` file in your project root:

```bash
cat > .env << EOF
AZURE_SPEECH_KEY=<your-speech-key>
AZURE_SPEECH_REGION=eastus
AZURE_TEXT_ANALYTICS_KEY=<your-text-analytics-key>
AZURE_TEXT_ANALYTICS_ENDPOINT=<your-endpoint>
AZURE_STORAGE_CONNECTION_STRING=<your-storage-connection-string>
AZURE_STORAGE_CONTAINER_NAME=meeting-audio-files
DEFAULT_LANGUAGE=en-US
ENABLE_SPEAKER_DIARIZATION=true
MAX_SPEAKERS=10
EOF
```

## Step 8: Verify Setup

Test your configuration:

```python
from meeting_processor.utils import ConfigManager

config = ConfigManager()
if config.validate_config():
    print("✓ Configuration is valid!")
else:
    print("✗ Configuration validation failed")
```

## Pricing Considerations

### Speech Services
- Standard tier (S0): Pay-as-you-go pricing
- See [Speech Services pricing](https://azure.microsoft.com/pricing/details/cognitive-services/speech-services/)

### Text Analytics
- Standard tier (S): Pay-as-you-go pricing
- See [Text Analytics pricing](https://azure.microsoft.com/pricing/details/cognitive-services/text-analytics/)

### Storage Account
- Standard LRS (Locally Redundant Storage)
- See [Storage pricing](https://azure.microsoft.com/pricing/details/storage/)

### Azure Functions
- Consumption plan: Pay only for execution time
- See [Functions pricing](https://azure.microsoft.com/pricing/details/functions/)

## Security Best Practices

1. **Use Managed Identities**: When possible, use managed identities instead of API keys
2. **Key Rotation**: Regularly rotate your API keys
3. **Network Security**: Restrict access using virtual networks and firewalls
4. **Key Vault**: Store secrets in Azure Key Vault for production deployments
5. **Monitoring**: Enable Azure Monitor and Application Insights for tracking

## Troubleshooting

### Issue: "Access Denied" errors

**Solution**: Verify your API keys are correct and your subscription has the necessary permissions.

### Issue: "Quota Exceeded" errors

**Solution**: Check your usage limits in Azure Portal and consider upgrading your tier.

### Issue: "Region Not Available" errors

**Solution**: Some services may not be available in all regions. Try a different region like `eastus`, `westus2`, or `westeurope`.

## Next Steps

- Complete the [Quick Start Guide](../README.md#quick-start)
- Review the [API Documentation](API.md)
- Set up [CI/CD with GitHub Actions](DEPLOYMENT.md)

## Additional Resources

- [Azure Cognitive Services Documentation](https://docs.microsoft.com/azure/cognitive-services/)
- [Azure Functions Documentation](https://docs.microsoft.com/azure/azure-functions/)
- [Azure CLI Reference](https://docs.microsoft.com/cli/azure/)
