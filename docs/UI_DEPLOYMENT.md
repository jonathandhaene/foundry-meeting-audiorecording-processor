# Deploying the Web UI to Azure

This guide explains how to deploy both the backend API and frontend UI to Azure.

## Architecture Overview

```
┌─────────────────────────┐
│  Azure Static Web App   │  (Frontend)
│  (React UI)             │
└───────────┬─────────────┘
            │ HTTPS
            ▼
┌─────────────────────────┐
│  Azure App Service      │  (Backend API)
│  (FastAPI + Python)     │
└─────────────────────────┘
```

## Prerequisites

- Azure CLI installed: `az --version`
- Azure subscription
- GitHub repository with the code

## Option 1: Azure App Service (Backend + Frontend)

### Step 1: Create Resource Group

```bash
az group create \
  --name meeting-transcription-rg \
  --location eastus
```

### Step 2: Deploy Backend API

Create an App Service Plan:

```bash
az appservice plan create \
  --name meeting-api-plan \
  --resource-group meeting-transcription-rg \
  --sku B1 \
  --is-linux
```

Create Web App:

```bash
az webapp create \
  --resource-group meeting-transcription-rg \
  --plan meeting-api-plan \
  --name meeting-transcription-api \
  --runtime "PYTHON:3.11"
```

Configure environment variables:

```bash
az webapp config appsettings set \
  --resource-group meeting-transcription-rg \
  --name meeting-transcription-api \
  --settings \
    AZURE_SPEECH_KEY="your_key" \
    AZURE_SPEECH_REGION="your_region" \
    AZURE_TEXT_ANALYTICS_KEY="your_key" \
    AZURE_TEXT_ANALYTICS_ENDPOINT="your_endpoint" \
    OPENAI_API_KEY="your_key"
```

Deploy the code:

```bash
# From project root
zip -r deploy.zip . -x "frontend/*" "tests/*" ".git/*"

az webapp deployment source config-zip \
  --resource-group meeting-transcription-rg \
  --name meeting-transcription-api \
  --src deploy.zip
```

Create startup command file `startup.sh`:

```bash
#!/bin/bash
cd /home/site/wwwroot
# Set API_HOST=0.0.0.0 for production to allow external access
export API_HOST=0.0.0.0
export API_PORT=8000
python -m uvicorn meeting_processor.api.app:app --host ${API_HOST} --port ${API_PORT}
```

Configure startup command:

```bash
az webapp config set \
  --resource-group meeting-transcription-rg \
  --name meeting-transcription-api \
  --startup-file startup.sh
```

### Step 3: Deploy Frontend

#### Option A: Static Web App

Create Static Web App:

```bash
az staticwebapp create \
  --name meeting-transcription-ui \
  --resource-group meeting-transcription-rg \
  --source https://github.com/your-org/your-repo \
  --location eastus2 \
  --branch main \
  --app-location "frontend" \
  --output-location "build"
```

#### Option B: App Service for Frontend

Create another App Service:

```bash
az webapp create \
  --resource-group meeting-transcription-rg \
  --plan meeting-api-plan \
  --name meeting-transcription-ui \
  --runtime "NODE:18-lts"
```

Build and deploy:

```bash
cd frontend
npm run build

# Deploy build folder
az webapp deployment source config-zip \
  --resource-group meeting-transcription-rg \
  --name meeting-transcription-ui \
  --src build.zip
```

### Step 4: Configure CORS

Enable CORS on the backend to allow frontend requests:

```bash
az webapp cors add \
  --resource-group meeting-transcription-rg \
  --name meeting-transcription-api \
  --allowed-origins "https://meeting-transcription-ui.azurewebsites.net"
```

## Option 2: Docker Deployment

### Backend Dockerfile

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY setup.py .

# Install the package
RUN pip install -e .

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose port
EXPOSE 8000

# Set default environment variables
# In Docker, default to 0.0.0.0 since container networking provides isolation
# Override at runtime with -e API_HOST=<value> if needed
ENV API_HOST=0.0.0.0
ENV API_PORT=8000

# Run the application using entrypoint script
ENTRYPOINT ["docker-entrypoint.sh"]
```

Create `docker-entrypoint.sh`:

```bash
#!/bin/bash
set -e

# Default environment variables (can be overridden at runtime)
: ${API_HOST:=0.0.0.0}
: ${API_PORT:=8000}

# Run uvicorn with exec to properly handle signals
exec python -m uvicorn meeting_processor.api.app:app --host "${API_HOST}" --port "${API_PORT}"
```

### Frontend Dockerfile

Create `frontend/Dockerfile`:

```dockerfile
# Build stage
FROM node:18-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

Create `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      # API server binding - set to 0.0.0.0 to accept connections from other containers
      - API_HOST=0.0.0.0
      - API_PORT=8000
      # Azure credentials
      - AZURE_SPEECH_KEY=${AZURE_SPEECH_KEY}
      - AZURE_SPEECH_REGION=${AZURE_SPEECH_REGION}
      - AZURE_TEXT_ANALYTICS_KEY=${AZURE_TEXT_ANALYTICS_KEY}
      - AZURE_TEXT_ANALYTICS_ENDPOINT=${AZURE_TEXT_ANALYTICS_ENDPOINT}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./tmp:/tmp

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
```

Deploy:

```bash
docker-compose up -d
```

### Deploy to Azure Container Instances

Build and push images:

```bash
# Create Azure Container Registry
az acr create \
  --resource-group meeting-transcription-rg \
  --name meetingtranscriptionacr \
  --sku Basic

# Build and push backend
az acr build \
  --registry meetingtranscriptionacr \
  --image meeting-api:latest \
  .

# Build and push frontend
az acr build \
  --registry meetingtranscriptionacr \
  --image meeting-ui:latest \
  ./frontend
```

Create container instances:

```bash
# Backend
az container create \
  --resource-group meeting-transcription-rg \
  --name meeting-api \
  --image meetingtranscriptionacr.azurecr.io/meeting-api:latest \
  --cpu 2 \
  --memory 4 \
  --registry-login-server meetingtranscriptionacr.azurecr.io \
  --registry-username $(az acr credential show --name meetingtranscriptionacr --query username -o tsv) \
  --registry-password $(az acr credential show --name meetingtranscriptionacr --query passwords[0].value -o tsv) \
  --dns-name-label meeting-api \
  --ports 8000 \
  --environment-variables \
    AZURE_SPEECH_KEY=your_key \
    AZURE_SPEECH_REGION=your_region

# Frontend
az container create \
  --resource-group meeting-transcription-rg \
  --name meeting-ui \
  --image meetingtranscriptionacr.azurecr.io/meeting-ui:latest \
  --cpu 1 \
  --memory 1 \
  --registry-login-server meetingtranscriptionacr.azurecr.io \
  --registry-username $(az acr credential show --name meetingtranscriptionacr --query username -o tsv) \
  --registry-password $(az acr credential show --name meetingtranscriptionacr --query passwords[0].value -o tsv) \
  --dns-name-label meeting-ui \
  --ports 80
```

## Option 3: GitHub Actions CI/CD

The repository includes a CI/CD pipeline. Configure these secrets in GitHub:

### Required Secrets

1. `AZURE_CREDENTIALS`: Azure service principal
   ```bash
   az ad sp create-for-rbac \
     --name "meeting-transcription-sp" \
     --role contributor \
     --scopes /subscriptions/{subscription-id}/resourceGroups/meeting-transcription-rg \
     --sdk-auth
   ```

2. `AZURE_WEBAPP_NAME`: Name of your backend App Service

3. `AZURE_STATIC_WEB_APP_TOKEN`: Deployment token for Static Web App
   ```bash
   az staticwebapp secrets list \
     --name meeting-transcription-ui \
     --query properties.apiKey
   ```

### Update `.github/workflows/deploy.yml`

The CI/CD pipeline will automatically:
1. Run tests
2. Build frontend
3. Deploy backend to App Service
4. Deploy frontend to Static Web App

## Environment Variables

Ensure these are set in your Azure App Service:

### Required
- `AZURE_SPEECH_KEY`
- `AZURE_SPEECH_REGION`
- `AZURE_TEXT_ANALYTICS_KEY`
- `AZURE_TEXT_ANALYTICS_ENDPOINT`

### Optional
- `OPENAI_API_KEY` (for Whisper API)
- `DEFAULT_LANGUAGE` (default: en-US)

## Security Considerations

1. **API Keys**: Always use Azure Key Vault for production
2. **CORS**: Restrict to your frontend domain only
3. **Authentication**: Implement Azure AD authentication
4. **HTTPS**: Always use HTTPS in production
5. **Rate Limiting**: Implement rate limiting on API endpoints

## Monitoring

Enable Application Insights:

```bash
az monitor app-insights component create \
  --app meeting-transcription-insights \
  --location eastus \
  --resource-group meeting-transcription-rg

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app meeting-transcription-insights \
  --resource-group meeting-transcription-rg \
  --query instrumentationKey -o tsv)

# Configure App Service
az webapp config appsettings set \
  --resource-group meeting-transcription-rg \
  --name meeting-transcription-api \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY=$INSTRUMENTATION_KEY
```

## Scaling

Configure autoscaling:

```bash
az monitor autoscale create \
  --resource-group meeting-transcription-rg \
  --resource meeting-transcription-api \
  --resource-type Microsoft.Web/serverfarms \
  --name autoscale-plan \
  --min-count 1 \
  --max-count 5 \
  --count 1

az monitor autoscale rule create \
  --resource-group meeting-transcription-rg \
  --autoscale-name autoscale-plan \
  --condition "Percentage CPU > 70 avg 5m" \
  --scale out 1
```

## Troubleshooting

### Check logs

```bash
# Backend logs
az webapp log tail \
  --resource-group meeting-transcription-rg \
  --name meeting-transcription-api

# Frontend logs
az staticwebapp show \
  --name meeting-transcription-ui \
  --resource-group meeting-transcription-rg
```

### Common Issues

1. **FFmpeg not found**: Ensure it's installed in the container
2. **Import errors**: Check Python path and package installation
3. **CORS errors**: Verify CORS configuration
4. **504 Gateway Timeout**: Increase timeout or optimize processing

## Cost Optimization

1. Use consumption-based pricing for Functions
2. Use B1 tier for development, scale to P1V2 for production
3. Configure auto-shutdown for dev environments
4. Use Azure Storage for file persistence instead of local disk

## References

- [Azure App Service Documentation](https://docs.microsoft.com/azure/app-service/)
- [Azure Static Web Apps](https://docs.microsoft.com/azure/static-web-apps/)
- [Azure Container Instances](https://docs.microsoft.com/azure/container-instances/)
