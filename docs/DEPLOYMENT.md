# Deployment Guide

This guide covers deployment options for the Meeting Audio Recording Processor.

## Table of Contents

1. [Local Deployment](#local-deployment)
2. [Azure Functions Deployment](#azure-functions-deployment)
3. [Azure Kubernetes Service (AKS)](#azure-kubernetes-service-aks)
4. [GitHub Actions CI/CD](#github-actions-cicd)
5. [Docker Deployment](#docker-deployment)

---

## Local Deployment

### Prerequisites

- Python 3.10+
- FFmpeg installed
- Azure credentials configured

### Setup

1. Clone and install:
```bash
git clone https://github.com/jonathandhaene/foundry-meeting-audiorecording-processor.git
cd foundry-meeting-audiorecording-processor
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your Azure credentials
```

3. Run:
```bash
python -m meeting_processor.pipeline audio_file.wav
```

---

## Azure Functions Deployment

Azure Functions provides serverless, event-driven processing for audio files.

### Prerequisites

- Azure CLI installed
- Azure Functions Core Tools installed
- Azure subscription

### Local Testing

```bash
cd azure_functions
func start
```

### Deploy via Azure CLI

1. Create resource group:
```bash
az group create \
  --name meeting-processor-rg \
  --location eastus
```

2. Create storage account:
```bash
az storage account create \
  --name meetingprocessorstorage \
  --resource-group meeting-processor-rg \
  --location eastus \
  --sku Standard_LRS
```

3. Create Function App:
```bash
az functionapp create \
  --resource-group meeting-processor-rg \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --name meeting-processor-func \
  --storage-account meetingprocessorstorage \
  --os-type Linux
```

4. Configure app settings:
```bash
az functionapp config appsettings set \
  --name meeting-processor-func \
  --resource-group meeting-processor-rg \
  --settings \
    AZURE_SPEECH_KEY="$AZURE_SPEECH_KEY" \
    AZURE_SPEECH_REGION="eastus" \
    AZURE_TEXT_ANALYTICS_KEY="$AZURE_TEXT_ANALYTICS_KEY" \
    AZURE_TEXT_ANALYTICS_ENDPOINT="$AZURE_TEXT_ANALYTICS_ENDPOINT" \
    DEFAULT_LANGUAGE="en-US" \
    ENABLE_SPEAKER_DIARIZATION="true" \
    MAX_SPEAKERS="10"
```

5. Deploy:
```bash
cd azure_functions
func azure functionapp publish meeting-processor-func
```

### Trigger Processing

Upload audio files to the `meeting-audio-files` container:

```bash
az storage blob upload \
  --account-name meetingprocessorstorage \
  --container-name meeting-audio-files \
  --name meeting.wav \
  --file meeting.wav
```

Results will be available in the `meeting-results` container.

---

## Azure Kubernetes Service (AKS)

For high-scale, containerized deployment.

### Prerequisites

- Docker installed
- kubectl installed
- Azure CLI installed

### Build Docker Image

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Set environment variables
ENV PYTHONPATH=/app/src

# Run the application
CMD ["python", "-m", "meeting_processor.pipeline"]
```

Build and push:

```bash
# Build image
docker build -t meeting-processor:latest .

# Tag for Azure Container Registry
docker tag meeting-processor:latest \
  yourregistry.azurecr.io/meeting-processor:latest

# Login to ACR
az acr login --name yourregistry

# Push image
docker push yourregistry.azurecr.io/meeting-processor:latest
```

### Deploy to AKS

1. Create AKS cluster:
```bash
az aks create \
  --resource-group meeting-processor-rg \
  --name meeting-processor-aks \
  --node-count 2 \
  --enable-addons monitoring \
  --generate-ssh-keys
```

2. Get credentials:
```bash
az aks get-credentials \
  --resource-group meeting-processor-rg \
  --name meeting-processor-aks
```

3. Create Kubernetes deployment (`k8s-deployment.yaml`):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meeting-processor
spec:
  replicas: 3
  selector:
    matchLabels:
      app: meeting-processor
  template:
    metadata:
      labels:
        app: meeting-processor
    spec:
      containers:
      - name: meeting-processor
        image: yourregistry.azurecr.io/meeting-processor:latest
        env:
        - name: AZURE_SPEECH_KEY
          valueFrom:
            secretKeyRef:
              name: azure-secrets
              key: speech-key
        - name: AZURE_SPEECH_REGION
          value: "eastus"
        - name: AZURE_TEXT_ANALYTICS_KEY
          valueFrom:
            secretKeyRef:
              name: azure-secrets
              key: text-analytics-key
        - name: AZURE_TEXT_ANALYTICS_ENDPOINT
          value: "https://your-endpoint.com"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
---
apiVersion: v1
kind: Service
metadata:
  name: meeting-processor-service
spec:
  selector:
    app: meeting-processor
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

4. Create secrets:
```bash
kubectl create secret generic azure-secrets \
  --from-literal=speech-key=$AZURE_SPEECH_KEY \
  --from-literal=text-analytics-key=$AZURE_TEXT_ANALYTICS_KEY
```

5. Deploy:
```bash
kubectl apply -f k8s-deployment.yaml
```

---

## GitHub Actions CI/CD

Automated deployment pipeline using GitHub Actions.

### Available Workflows

The repository includes two deployment workflows:

1. **`.github/workflows/ci-cd.yml`** - Comprehensive CI/CD pipeline
2. **`.github/workflows/deploy-to-azure.yml`** - Simplified Azure deployment

### Setup

#### Required GitHub Secrets

Go to Settings → Secrets and add:
- `AZURE_CREDENTIALS`: Service principal credentials for Azure login
- `AZURE_WEBAPP_NAME`: Your Azure App Service name
- `AZURE_FUNCTION_APP_NAME`: Your function app name (for ci-cd.yml)
- `AZURE_FUNCTION_PUBLISH_PROFILE`: Function app publish profile (for ci-cd.yml)

#### Get Azure Credentials

Create a service principal with contributor role:

```bash
az ad sp create-for-rbac \
  --name "github-actions-sp" \
  --role contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/meeting-processor-rg \
  --sdk-auth
```

Copy the JSON output to `AZURE_CREDENTIALS` secret. Example format:
```json
{
  "clientId": "<client-id>",
  "clientSecret": "<client-secret>",
  "subscriptionId": "<subscription-id>",
  "tenantId": "<tenant-id>"
}
```

#### Get Publish Profile (Optional)

For the ci-cd.yml workflow:

```bash
az functionapp deployment list-publishing-profiles \
  --name meeting-processor-func \
  --resource-group meeting-processor-rg \
  --xml
```

Copy the output to `AZURE_FUNCTION_PUBLISH_PROFILE` secret.

### Deploy to Azure Workflow

The **deploy-to-azure.yml** workflow provides a streamlined deployment process:

#### Features:
- **Triggers**: Automatically on push/pull_request to `main` branch, or manually
- **Build**: Installs dependencies for both Python backend and React frontend
- **Deploy**: Publishes the application to Azure App Service

#### What it does:

1. **Build Job:**
   - Sets up Python 3.11 and Node.js 18
   - Installs FFmpeg and system dependencies
   - Caches pip dependencies for faster builds
   - Builds Python package and React frontend
   - Uploads artifacts for deployment

2. **Deploy Job:**
   - Only runs on push to main branch
   - Downloads build artifacts
   - Logs into Azure using service principal
   - Deploys to Azure Web App using `azure/webapps-deploy@v2`

#### Usage:

The workflow automatically triggers on:
- Push to `main` branch (builds and deploys)
- Pull request to `main` branch (builds only, no deployment)
- Manual trigger via workflow_dispatch

### CI/CD Pipeline Workflow

The **ci-cd.yml** workflow provides comprehensive testing and multi-service deployment:

#### What it does:

1. **On Push/PR:**
   - Runs tests on multiple Python versions (3.10, 3.11)
   - Performs linting and type checking
   - Generates coverage reports
   - Builds Python package and React frontend

2. **On Push to main:**
   - Deploys to Azure Functions
   - Deploys backend API to Azure Web App
   - Deploys frontend to Azure Static Web App
   - Updates production environment

### Manual Deployment Trigger

You can manually trigger either workflow:

1. Go to Actions tab in GitHub
2. Select the workflow you want to run:
   - "Deploy to Azure" - for streamlined deployment
   - "CI/CD Pipeline" - for comprehensive testing and deployment
3. Click "Run workflow"
4. Select branch and run

---

## Docker Deployment

### Build Docker Image

```bash
docker build -t meeting-processor:latest .
```

### Run Locally

```bash
docker run -it \
  -e AZURE_SPEECH_KEY=$AZURE_SPEECH_KEY \
  -e AZURE_SPEECH_REGION=eastus \
  -e AZURE_TEXT_ANALYTICS_KEY=$AZURE_TEXT_ANALYTICS_KEY \
  -e AZURE_TEXT_ANALYTICS_ENDPOINT=$AZURE_TEXT_ANALYTICS_ENDPOINT \
  -v $(pwd)/audio:/app/audio \
  -v $(pwd)/output:/app/output \
  meeting-processor:latest \
  python -m meeting_processor.pipeline /app/audio/meeting.wav --output /app/output
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  meeting-processor:
    build: .
    environment:
      - AZURE_SPEECH_KEY=${AZURE_SPEECH_KEY}
      - AZURE_SPEECH_REGION=eastus
      - AZURE_TEXT_ANALYTICS_KEY=${AZURE_TEXT_ANALYTICS_KEY}
      - AZURE_TEXT_ANALYTICS_ENDPOINT=${AZURE_TEXT_ANALYTICS_ENDPOINT}
    volumes:
      - ./audio:/app/audio
      - ./output:/app/output
    command: python -m meeting_processor.pipeline /app/audio/meeting.wav --output /app/output
```

Run with:
```bash
docker-compose up
```

---

## Monitoring and Logging

### Application Insights

Enable Application Insights for Azure Functions:

```bash
az monitor app-insights component create \
  --app meeting-processor-insights \
  --location eastus \
  --resource-group meeting-processor-rg

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app meeting-processor-insights \
  --resource-group meeting-processor-rg \
  --query instrumentationKey -o tsv)

# Configure Function App
az functionapp config appsettings set \
  --name meeting-processor-func \
  --resource-group meeting-processor-rg \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY=$INSTRUMENTATION_KEY
```

### Log Analytics

View logs in Azure Portal or via CLI:

```bash
az monitor app-insights query \
  --app meeting-processor-insights \
  --analytics-query 'traces | order by timestamp desc | limit 100'
```

---

## Scaling Considerations

### Azure Functions
- Consumption Plan: Auto-scales based on load
- Premium Plan: Pre-warmed instances for faster startup
- Dedicated Plan: For predictable workloads

### AKS
- Horizontal Pod Autoscaler: Scale based on CPU/memory
- Cluster Autoscaler: Add/remove nodes automatically

Example HPA configuration:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: meeting-processor-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: meeting-processor
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## Troubleshooting

### Common Issues

1. **Function timeout**: Increase timeout in `host.json`
2. **Out of memory**: Increase memory allocation or optimize batch size
3. **Cold start**: Use Premium Plan or App Service Plan
4. **Deployment failures**: Check Azure CLI version and credentials

### Health Checks

Add health check endpoint:

```python
@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    })
```

---

## Cost Optimization

1. **Use consumption plans** for variable workloads
2. **Enable auto-scaling** to avoid over-provisioning
3. **Use Azure Spot VMs** for non-critical workloads
4. **Implement caching** to reduce API calls
5. **Monitor usage** with Azure Cost Management

---

## Next Steps

- Set up monitoring and alerts
- Implement backup and disaster recovery
- Configure custom domains and SSL
- Optimize for your specific workload

## Additional Resources

- [Azure Functions Documentation](https://docs.microsoft.com/azure/azure-functions/)
- [AKS Documentation](https://docs.microsoft.com/azure/aks/)
- [GitHub Actions Documentation](https://docs.github.com/actions)
