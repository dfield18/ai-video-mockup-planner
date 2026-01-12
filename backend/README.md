# AI Video Mockup Planner - Backend

A production-ready system for generating structured shot plans and visual mockups from video scripts. Built with FastAPI, Python, and Google Gemini AI.

## Features

- **Domain-Agnostic**: Works with any type of video content (drama, documentary, commercial, etc.)
- **Versioned Assets**: All assets (scripts, plans, shots, images) are versioned and never overwritten
- **Continuity Validation**: Automatic validation and repair of shot plans for continuity errors
- **User-in-the-Loop**: Accept, edit, or regenerate images with full version history
- **Strict JSON Contracts**: All LLM interactions use strict JSON schemas with validation
- **Modular Architecture**: Local filesystem storage (easily swappable to database)
- **Async-Ready**: Job tracking system ready for async operations

## Architecture

```
ai_video_mockup_planner/
├── config.py           # Configuration management
├── schemas.py          # Pydantic models for all entities
├── storage.py          # Local filesystem storage layer
├── prompts.py          # LLM prompt templates
├── gemini_client.py    # Google Gemini API wrapper
├── continuity.py       # Continuity validation and repair
├── prompt_builders.py  # Image prompt construction
├── plan_editing.py     # Plan patching operations
├── image_pipeline.py   # Image generation and editing
├── exports.py          # Export functionality
├── pipeline.py         # Main orchestration logic
└── api.py              # FastAPI REST API
```

## Installation

1. **Clone and setup**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your GOOGLE_API_KEY
   ```

3. **Run the server**:
   ```bash
   uvicorn ai_video_mockup_planner.api:app --reload
   ```

   Server will start at `http://localhost:8000`

4. **API documentation**:
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

## Running Tests

```bash
pytest tests/ -v
```

Tests cover:
- Versioning (assets never overwritten)
- Plan patching (new versions created)
- Continuity validation (missing entities, state conflicts)
- Regeneration scopes (shot/scene/asset targeting)

## Complete Walkthrough with curl

This walkthrough demonstrates the full pipeline from script to storyboard.

### 1. Health Check

```bash
curl http://localhost:8000/health
```

### 2. Create a Project

```bash
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Mystery Short Film",
    "user_id": "user123"
  }'
```

Save the `project_id` from the response (e.g., `proj_abc123`).

### 3. Create a Script

```bash
PROJECT_ID="proj_abc123"  # Replace with actual project_id

curl -X POST http://localhost:8000/script \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "'$PROJECT_ID'",
    "title": "The Discovery",
    "content": "INT. DETECTIVE OFFICE - NIGHT\n\nDETECTIVE SARAH (40s, sharp-eyed, wearing a gray suit) studies crime scene photos spread across her desk. The office is dimly lit, venetian blinds casting shadows.\n\nShe picks up a magnifying glass, examining one photo closely. Her eyes widen.\n\nSARAH\n(to herself)\nWait... this changes everything.\n\nShe grabs her coat and rushes out.\n\nEXT. WAREHOUSE DISTRICT - NIGHT\n\nSarah arrives at an abandoned warehouse. Rain falls steadily. She pulls out her flashlight and enters cautiously.\n\nINT. WAREHOUSE - NIGHT\n\nHer flashlight beam cuts through the darkness. She discovers a hidden door behind old crates. Behind it: a wall covered in photographs and newspaper clippings, all connected by red string.\n\nSarah studies the wall, pieces falling into place. She pulls out her phone to call for backup.\n\nFADE OUT."
  }'
```

### 4. Generate Plan from Script

This extracts structured metadata (characters, locations, scenes, etc.):

```bash
curl -X POST http://localhost:8000/plan \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "'$PROJECT_ID'",
    "preferences": {
      "style": "cinematic noir",
      "visual_realism": "high",
      "pacing": "medium",
      "target_duration_s": 45
    }
  }'
```

This will:
- Parse the script using Gemini
- Extract characters (Detective Sarah)
- Extract locations (Office, Warehouse District, Warehouse Interior)
- Identify scenes and beats
- Return a structured PlanAsset

Save the plan to view:
```bash
curl http://localhost:8000/plan/$PROJECT_ID | jq . > plan.json
```

### 5. Patch the Plan (Edit Character)

Let's make Detective Sarah older:

```bash
curl -X POST http://localhost:8000/plan/patch \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "'$PROJECT_ID'",
    "patches": [
      {
        "path": "characters[CHAR_01].identity_lock",
        "op": "replace",
        "value": "Woman in her 50s, sharp-eyed, salt-and-pepper hair, weathered face showing years of experience"
      },
      {
        "path": "characters[CHAR_01].description",
        "op": "replace",
        "value": "Veteran detective, late 50s, approaching retirement but still sharp"
      }
    ]
  }'
```

This creates a **new version** of the plan (v2) without modifying v1.

### 6. Generate Shot Plan

Generate detailed shots with camera angles and continuity:

```bash
curl -X POST http://localhost:8000/shots \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "'$PROJECT_ID'"
  }'
```

This will:
- Generate individual shots (S001, S002, S003, etc.)
- Assign camera angles and movements
- Add continuity locks
- Validate for continuity errors
- Auto-repair if issues found

View the shot plan:
```bash
curl http://localhost:8000/shots/$PROJECT_ID | jq . > shots.json
```

### 7. Generate Images for Shot Frames

Generate visual mockups for all shots:

```bash
curl -X POST http://localhost:8000/images/generate \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "'$PROJECT_ID'",
    "scope": {
      "scope_type": "project"
    }
  }'
```

**Note**: In MVP mode, this creates placeholder images (`placeholder://...`). In production, these would be actual API calls to image generation services.

You can also generate for specific scopes:

**Single shot only**:
```bash
curl -X POST http://localhost:8000/images/generate \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "'$PROJECT_ID'",
    "scope": {
      "scope_type": "shot",
      "shot_id": "S003"
    }
  }'
```

**All shots in a scene**:
```bash
curl -X POST http://localhost:8000/images/generate \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "'$PROJECT_ID'",
    "scope": {
      "scope_type": "scene",
      "scene_id": "SC001"
    }
  }'
```

### 8. List Generated Images

```bash
curl "http://localhost:8000/assets/images?project_id=$PROJECT_ID" | jq .
```

Filter by type:
```bash
curl "http://localhost:8000/assets/images?project_id=$PROJECT_ID&asset_type=shot_frame" | jq .
```

### 9. Edit an Image

Let's say shot S003 needs more dramatic shadows. First, get the image asset ID from step 8, then:

```bash
IMAGE_ID="img_shot_S003_xyz_v1"  # Replace with actual image asset ID

curl -X POST http://localhost:8000/image/action \
  -H "Content-Type: application/json" \
  -d '{
    "action": "edit",
    "image_asset_id": "'$IMAGE_ID'",
    "feedback": "Make the shadows more dramatic and add more contrast. The flashlight beam should be more prominent.",
    "lock_profile": {
      "preserve_identity": true,
      "preserve_wardrobe": true,
      "preserve_location_layout": true,
      "banned_elements": ["bright lighting", "daylight"]
    }
  }'
```

This will:
- Interpret the feedback using Gemini
- Generate an edit delta (add dramatic shadows, increase contrast)
- Build a new prompt incorporating the changes
- Create a **new version** (v2) of the image
- Original image (v1) remains unchanged

### 10. Regenerate an Image

If you want a fresh take while preserving certain elements:

```bash
curl -X POST http://localhost:8000/image/action \
  -H "Content-Type: application/json" \
  -d '{
    "action": "regenerate",
    "image_asset_id": "'$IMAGE_ID'",
    "lock_profile": {
      "preserve_identity": true,
      "preserve_wardrobe": true,
      "preserve_location_layout": true,
      "preserve_time_of_day": true,
      "must_keep_elements": ["flashlight", "red string wall"]
    }
  }'
```

### 11. Accept an Image

Once satisfied with an image:

```bash
curl -X POST http://localhost:8000/image/action \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept",
    "image_asset_id": "'$IMAGE_ID'"
  }'
```

This marks the image as `accepted` (ready for production).

### 12. Export Storyboard

Export the complete storyboard with all assets:

```bash
curl -X POST http://localhost:8000/export/storyboard \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "'$PROJECT_ID'",
    "include_images": true,
    "format": "json"
  }' | jq . > storyboard.json
```

Export as CSV-ready format:
```bash
curl -X POST http://localhost:8000/export/storyboard \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "'$PROJECT_ID'",
    "include_images": true,
    "format": "csv"
  }' | jq . > storyboard_csv.json
```

### 13. Export Individual Assets

**Characters CSV**:
```bash
curl "http://localhost:8000/export/characters/$PROJECT_ID" | jq .
```

**Shots CSV**:
```bash
curl "http://localhost:8000/export/shots/$PROJECT_ID" | jq .
```

**Full Plan JSON**:
```bash
curl "http://localhost:8000/export/plan/$PROJECT_ID" | jq .
```

## Key Concepts

### Versioning

All assets use a stable ID + version number:
- `script_abc_v1`, `script_abc_v2` (same script, different versions)
- `plan_xyz_v1`, `plan_xyz_v2` (same plan, patched)
- `img_shot_S001_123_v1`, `img_shot_S001_123_v2` (same image, edited)

**Nothing is ever overwritten**. Each edit/regenerate creates a new version.

### Lock Profiles

Lock profiles control what must be preserved during image editing/regeneration:

```json
{
  "preserve_identity": true,      // Keep character faces/appearance
  "preserve_wardrobe": true,       // Keep clothing
  "preserve_style": true,          // Keep visual style
  "preserve_camera": false,        // Allow camera angle changes
  "preserve_pose": false,          // Allow pose changes
  "preserve_location_layout": true, // Keep spatial arrangement
  "preserve_time_of_day": true,    // Keep lighting/time
  "banned_elements": ["cars", "phones"], // Never include these
  "must_keep_elements": ["red jacket", "briefcase"] // Always include these
}
```

### Continuity Locks

Each shot has a `continuity_lock` field describing constraints that MUST be preserved:

```
"Character A wears red jacket and holds briefcase in left hand;
Location is daytime office with glass walls;
Character B stands to the right of Character A"
```

These are enforced across all image variations of that shot.

### Regeneration Scopes

Control what gets regenerated:

- **project**: Everything (style frame, characters, locations, all shots)
- **scene**: All shots in a specific scene
- **shot**: Single shot only
- **asset**: Specific asset type (e.g., all character references)

## Storage Structure

```
storage/
└── proj_abc123/
    ├── project.json
    ├── _counters.json
    ├── scripts/
    │   ├── script_xyz_v1.json
    │   ├── script_xyz_v2.json
    │   └── _index.json
    ├── plans/
    │   ├── plan_123_v1.json
    │   ├── plan_123_v2.json
    │   └── _index.json
    ├── shot_plans/
    │   ├── shotplan_456_v1.json
    │   └── _index.json
    ├── images/
    │   ├── img_shot_S001_789_v1.json
    │   ├── img_shot_S001_789_v2.json
    │   └── _index.json
    ├── jobs/
    │   └── job_abc.json
    └── traces/
        └── trace_xyz.json
```

## Environment Variables

```bash
# Required
GOOGLE_API_KEY=your_api_key_here

# Optional (with defaults)
GEMINI_MODEL=gemini-1.5-pro
TEMPERATURE=0.4
MAX_TOKENS=4096
STORAGE_DIR=./storage
```

## API Endpoints

### Projects
- `POST /projects` - Create project
- `GET /projects/{project_id}` - Get project
- `GET /projects` - List all projects

### Scripts
- `POST /script` - Create/update script
- `GET /script/{project_id}` - Get active script

### Plans
- `POST /plan` - Generate plan from script
- `POST /plan/patch` - Apply patches to plan
- `GET /plan/{project_id}` - Get active plan

### Shots
- `POST /shots` - Generate shot plan
- `GET /shots/{project_id}` - Get active shot plan

### Images
- `POST /images/generate` - Generate images for scope
- `POST /image/action` - Accept/edit/regenerate image
- `GET /assets/images` - List images with filters

### Jobs
- `GET /jobs/{job_id}` - Get job status
- `GET /jobs` - List jobs for project

### Exports
- `GET /export/plan/{project_id}` - Export plan JSON
- `GET /export/characters/{project_id}` - Export characters CSV
- `GET /export/shots/{project_id}` - Export shots CSV
- `POST /export/storyboard` - Export complete storyboard

## Development

### Adding Real Image Generation

To integrate real image generation APIs (Veo, DALL-E, etc.), update `image_pipeline.py`:

1. Replace stub implementations in `_generate_shot_frame()`, etc.
2. Add actual API calls to image generation service
3. Store returned image URLs in `image_url` field
4. Keep all prompt construction logic unchanged

Example:
```python
# In image_pipeline.py
def _generate_shot_frame(...):
    prompt, negative_prompt = build_shot_frame_prompt(...)

    # Replace this stub:
    # image_url = f"placeholder://shot_{shot.shot_id}_{generate_id()}.jpg"

    # With actual API call:
    image_url = veo_client.generate_video_frame(
        prompt=prompt,
        negative_prompt=negative_prompt,
        aspect_ratio=plan.project_bible.aspect_ratio
    )

    # Rest remains the same...
```

### Switching to Database Storage

To replace filesystem storage with a database:

1. Implement new `DatabaseRepository` class matching `StorageRepository` interface
2. Update `storage.py` to use database instead of JSON files
3. All other code remains unchanged (modular architecture)

## Production Considerations

- **Authentication**: Add API key or OAuth middleware
- **Rate Limiting**: Add rate limiting for LLM calls
- **Async Workers**: Move LLM calls to background workers (Celery, RQ)
- **Caching**: Cache LLM responses for repeated prompts
- **Image Storage**: Use S3/GCS for actual image files
- **Database**: Replace filesystem with PostgreSQL + versioned tables
- **Monitoring**: Add APM (Sentry, DataDog) and LLM call tracing

## License

MIT

## Support

For issues and questions, please open a GitHub issue.
