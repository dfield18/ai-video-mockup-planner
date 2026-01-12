# AI Video Mockup Planner

A production-ready system for generating structured shot plans and visual mockups from video scripts.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/new)

## Features

- **Domain-Agnostic**: Works with any type of video content
- **Versioned Assets**: All assets are versioned and never overwritten
- **Continuity Validation**: Automatic validation and repair of shot plans
- **User-in-the-Loop**: Accept, edit, or regenerate images with full version history
- **Strict JSON Contracts**: All LLM interactions use strict JSON schemas
- **Modular Architecture**: Filesystem storage (easily swappable to database)

## Quick Start

### Local Development

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# Run server
uvicorn ai_video_mockup_planner.api:app --reload --port 8765
```

Visit http://localhost:8765/docs for interactive API documentation.

### Deploy to Railway

1. **Click the "Deploy on Railway" button above** OR:

2. **Manual deployment**:
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli

   # Login
   railway login

   # Initialize project
   railway init

   # Add environment variable
   railway variables set GOOGLE_API_KEY=your_api_key_here

   # Deploy
   railway up
   ```

3. **Set environment variables** in Railway dashboard:
   - `GOOGLE_API_KEY` - Your Google AI API key (required)
   - `GEMINI_MODEL` - Model name (optional, default: gemini-1.5-pro)
   - `STORAGE_DIR` - Storage directory (optional, default: ./storage)

### Testing

```bash
cd backend
pytest tests/ -v
```

All tests pass without requiring a real API key (uses stub mode).

## Documentation

- **Backend README**: [backend/README.md](backend/README.md) - Complete API documentation with curl walkthrough
- **Frontend Spec**: [frontend/README.md](frontend/README.md) - Intended UI flow and features

## Architecture

```
ai-video-mockup-planner/
├── backend/              # Python/FastAPI backend
│   ├── ai_video_mockup_planner/  # Core modules
│   ├── tests/           # Comprehensive test suite
│   └── README.md        # Detailed documentation
└── frontend/            # Placeholder for future UI
```

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, Pydantic
- **LLM**: Google Gemini API
- **Storage**: Local filesystem (modular, swappable)
- **Testing**: pytest

## API Endpoints

- `GET /health` - Health check
- `POST /projects` - Create project
- `POST /script` - Create/update script
- `POST /plan` - Generate plan from script
- `POST /plan/patch` - Apply patches to plan
- `POST /shots` - Generate shot plan
- `POST /images/generate` - Generate images
- `POST /image/action` - Accept/edit/regenerate image
- `GET /assets/images` - List images
- `POST /export/storyboard` - Export complete storyboard

See [backend/README.md](backend/README.md) for complete API documentation.

## Contributing

This project is open source. Feel free to open issues or submit pull requests.

## License

MIT
