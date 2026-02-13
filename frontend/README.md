# Meeting Transcription Web UI

React-based user interface for the Meeting Audio Transcription service.

## Features

- 📤 Audio file upload with drag & drop support
- 🎙️ Multiple transcription methods (Azure Speech, Whisper Local, Whisper API)
- ⚙️ Configurable options (language, diarization, model size)
- 📊 Real-time job status tracking
- 📝 Interactive results display with segments and timestamps
- 🔍 NLP analysis visualization (key phrases, sentiment)
- 💾 Job history and comparison

## Development

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

### Install Dependencies

```bash
npm install
```

### Start Development Server

```bash
npm start
```

Opens at `http://localhost:3000` with hot reload.

### Build for Production

```bash
npm run build
```

Creates optimized production build in `build/` folder.

### Run Tests

```bash
npm test
```

## Configuration

The UI connects to the backend API via the proxy configured in `package.json`:

```json
{
  "proxy": "http://localhost:8000"
}
```

For production, update API endpoint in the build configuration.

## Deployment

### Option 1: Azure Static Web App

```bash
npm run build
az staticwebapp create --name meeting-ui --resource-group rg --source .
```

### Option 2: Docker

```bash
docker build -t meeting-ui .
docker run -p 80:80 meeting-ui
```

### Option 3: Nginx

Copy build folder to nginx:

```bash
npm run build
cp -r build/* /var/www/html/
```

## Project Structure

```
src/
├── App.js          # Main application component
├── App.css         # Application styles
├── index.js        # React entry point
└── index.css       # Global styles

public/
├── index.html      # HTML template
└── ...
```

## API Integration

The UI communicates with these backend endpoints:

- `POST /api/transcribe` - Upload file and start transcription
- `GET /api/jobs/{id}` - Get job status and results
- `GET /api/jobs` - List all jobs
- `DELETE /api/jobs/{id}` - Delete a job

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

MIT
