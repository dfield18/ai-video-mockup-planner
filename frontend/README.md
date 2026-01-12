# AI Video Mockup Planner - Frontend (Placeholder)

This directory is reserved for the future frontend implementation.

## Intended UI Flow

The frontend would provide a web interface for the complete pipeline:

### 1. Project Setup
- Create new project
- Name and configure project settings

### 2. Script Input
- Text editor for script entry
- Support for uploading script files
- Auto-save drafts

### 3. Plan Generation & Review
- Trigger plan generation from script
- Visual review of extracted metadata:
  - Character cards with identity locks
  - Location cards with visual descriptions
  - Scene breakdown timeline
- Edit capabilities:
  - Inline editing of character details
  - Modify location descriptions
  - Adjust project settings

### 4. Shot Plan Review
- Visual shot list with thumbnails (when available)
- Timeline view showing shot sequence
- Shot details panel:
  - Camera setup visualization
  - Action beats
  - Continuity notes
- Continuity validator results with warnings/errors

### 5. Image Generation & Iteration
- Gallery view of all generated images
- Per-image controls:
  - Accept button
  - Edit with feedback text
  - Regenerate with lock profile controls
- Version history slider for each image
- Side-by-side comparison view

### 6. Storyboard View
- Complete storyboard layout
- Shot cards with:
  - Image mockup
  - Shot ID and timing
  - Camera notes
  - Action description
- Print/export options

### 7. Export Panel
- Download options:
  - Full storyboard PDF
  - Characters CSV
  - Shots CSV
  - Complete JSON

## Technology Stack (Suggested)

- **Framework**: React or Vue.js
- **State Management**: Redux or Pinia
- **UI Components**: Material-UI or Tailwind CSS
- **API Client**: Axios or Fetch
- **File Upload**: react-dropzone
- **Image Display**: react-image-gallery
- **Timeline**: vis-timeline or custom
- **PDF Export**: jsPDF or backend-generated

## Key Features

- **Real-time collaboration** (future): Multiple users editing same project
- **Undo/redo**: Leverage versioned assets for full history
- **Keyboard shortcuts**: Fast navigation and actions
- **Responsive design**: Works on desktop and tablet
- **Dark mode**: Toggle for late-night editing sessions
- **Drag-and-drop**: Reorder shots, upload files

## Getting Started (Future)

When implemented:

```bash
npm install
npm run dev
```

## Environment Variables

```env
VITE_API_URL=http://localhost:8000
```

## Development Notes

- Frontend communicates with backend via REST API
- All state comes from backend (frontend is stateless)
- Image URLs in MVP are placeholders; production would show actual images
- Version history UI shows timeline of edits per asset

---

**Status**: Placeholder only. Backend is fully functional and ready for frontend integration.
