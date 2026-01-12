"""
LLM prompt templates for AI Video Mockup Planner.
All prompts are domain-agnostic and demand strict JSON output.
"""

# ────────────────────────────────────────────────────────────────────────────────
# EXTRACT PLAN PROMPT
# ────────────────────────────────────────────────────────────────────────────────

EXTRACT_PLAN_PROMPT_V1 = """You are a film pre-production assistant. Extract structured planning metadata from the provided script.

SCRIPT:
{script_content}

USER PREFERENCES:
{preferences_json}

OUTPUT REQUIREMENTS:
Return ONLY a valid JSON object (no markdown, no code fences, no extra text) matching this exact schema:

{{
  "schema_version": "1.0",
  "project_bible": {{
    "title": "string",
    "genre": "string",
    "tone": "string",
    "style": "string (e.g., 'cinematic realism', 'stylized animation')",
    "aspect_ratio": "string (e.g., '16:9', '2.35:1')",
    "target_duration_s": number,
    "visual_realism": "string (low/medium/high)",
    "pacing": "string (slow/medium/fast)"
  }},
  "characters": [
    {{
      "character_id": "string (e.g., 'CHAR_01')",
      "name": "string",
      "description": "string (brief role/personality)",
      "identity_lock": "string (detailed physical description for image generation: age, gender, build, facial features, hair, ethnicity)",
      "wardrobe_lock": "string (default outfit description)",
      "key_props": ["string"],
      "role": "string (protagonist/antagonist/supporting)"
    }}
  ],
  "locations": [
    {{
      "location_id": "string (e.g., 'LOC_01')",
      "name": "string",
      "description": "string (brief function)",
      "location_lock": "string (detailed visual description: architecture, lighting, key objects, atmosphere)",
      "time_of_day": "string (dawn/morning/midday/afternoon/dusk/night)",
      "weather": "string (clear/cloudy/rain/snow/fog)"
    }}
  ],
  "props_wardrobe": [
    {{
      "prop_id": "string (e.g., 'PROP_01')",
      "name": "string",
      "description": "string",
      "category": "string (prop/wardrobe/vehicle/weapon)"
    }}
  ],
  "scenes": [
    {{
      "scene_id": "string (e.g., 'SC001')",
      "scene_index": number,
      "summary": "string (1-2 sentences)",
      "location_id": "string (reference to locations array)",
      "time_of_day": "string",
      "beats": [
        {{
          "beat_index": number,
          "action": "string",
          "emotional_tone": "string"
        }}
      ],
      "characters_present": ["string (character_ids)"]
    }}
  ]
}}

INSTRUCTIONS:
- Use filmmaking primitives only (no domain-specific jargon).
- Generate stable IDs (CHAR_01, LOC_01, PROP_01, SC001) that can be referenced.
- identity_lock and location_lock must be detailed enough for image generation.
- wardrobe_lock should describe the character's typical outfit.
- Merge user preferences with extracted metadata.
- Return ONLY the JSON object. No markdown, no explanations, no extra text.
"""

# ────────────────────────────────────────────────────────────────────────────────
# GENERATE SHOTS PROMPT
# ────────────────────────────────────────────────────────────────────────────────

GENERATE_SHOTS_PROMPT_V1 = """You are a cinematographer and shot planner. Generate a detailed shot list from the provided plan.

PLAN METADATA:
{plan_json}

TARGET DURATION: {target_duration_s} seconds
PACING: {pacing}

OUTPUT REQUIREMENTS:
Return ONLY a valid JSON object (no markdown, no code fences, no extra text) matching this exact schema:

{{
  "schema_version": "1.0",
  "shots": [
    {{
      "shot_id": "string (e.g., 'S001', 'S002')",
      "scene_id": "string (reference to scene)",
      "shot_index_in_scene": number,
      "duration_s": number,
      "location_id": "string (reference to location)",
      "characters": ["string (character_ids present in shot)"],
      "shot_type": "string (wide/medium/closeup/extreme_closeup/over_shoulder/insert)",
      "camera": {{
        "shot_type": "string",
        "angle": "string (high/eye_level/low/dutch)",
        "movement": "string (static/pan/tilt/dolly/track/handheld)",
        "lens": "string (optional: wide/normal/telephoto)"
      }},
      "action_beats": ["string (specific actions visible in this shot)"],
      "dialogue": "string or null (any dialogue spoken in this shot)",
      "audio_notes": "string or null (sound effects, music cues)",
      "continuity_lock": "string (CRITICAL: constraints that MUST be preserved across all variations of this shot, e.g., 'Character A wears red jacket, holds briefcase in left hand; Location is daytime with clear sky; Character B stands to the right of Character A')",
      "negative_prompt": "string (what to avoid in image generation)",
      "state_in": {{
        "props_held": ["string (prop_ids)"],
        "wardrobe_state": {{"character_id": "description"}},
        "injuries_visible": ["string"],
        "time_of_day": "string",
        "weather": "string",
        "custom": {{}}
      }},
      "state_out": {{
        "props_held": ["string"],
        "wardrobe_state": {{"character_id": "description"}},
        "injuries_visible": ["string"],
        "time_of_day": "string",
        "weather": "string",
        "custom": {{}}
      }}
    }}
  ]
}}

INSTRUCTIONS:
- Generate shot_ids sequentially (S001, S002, S003...).
- Allocate duration_s to meet target_duration_s and pacing.
- For each shot, specify continuity_lock with critical constraints.
- state_in and state_out track continuity (props, wardrobe, injuries, etc).
- Within a scene, state_out of shot N must match state_in of shot N+1.
- negative_prompt should list what to avoid (e.g., "blurry, low quality, anachronisms").
- Do NOT generate veo_prompt field (built separately).
- Return ONLY the JSON object. No markdown, no explanations, no extra text.
"""

# ────────────────────────────────────────────────────────────────────────────────
# CONTINUITY CRITIC PROMPT
# ────────────────────────────────────────────────────────────────────────────────

CONTINUITY_CRITIC_PROMPT_V1 = """You are a script supervisor checking for continuity issues in a shot plan.

PLAN METADATA:
{plan_json}

SHOT PLAN:
{shot_plan_json}

OUTPUT REQUIREMENTS:
Return ONLY a valid JSON object (no markdown, no code fences, no extra text):

{{
  "schema_version": "1.0",
  "qa_issues": [
    {{
      "severity": "error|warning|info",
      "issue_type": "string (missing_entity/state_conflict/continuity_gap/other)",
      "message": "string (clear description of the issue)",
      "suggested_fix": "string (how to resolve it)",
      "shot_id": "string or null"
    }}
  ]
}}

CHECK FOR:
1. Missing entities: shots reference characters/locations/props not defined in plan.
2. State conflicts: within a scene, state_out of shot N doesn't match state_in of shot N+1.
3. Continuity gaps: time_of_day, weather, wardrobe, props held changes unexpectedly.
4. Missing required fields: continuity_lock, negative_prompt must be present for each shot.
5. Shot ordering: shot_index_in_scene must be sequential within each scene.

Return ONLY the JSON object. No markdown, no explanations, no extra text.
"""

# ────────────────────────────────────────────────────────────────────────────────
# REPAIR JSON PROMPT
# ────────────────────────────────────────────────────────────────────────────────

REPAIR_JSON_PROMPT_V1 = """You are a JSON repair assistant. The following JSON has issues that must be fixed.

ORIGINAL JSON (with issues):
{broken_json}

QA ISSUES FOUND:
{qa_issues_json}

OUTPUT REQUIREMENTS:
Return ONLY the corrected JSON object (no markdown, no code fences, no extra text).
Fix all issues listed in the QA report while preserving the original structure and intent.

Return ONLY the corrected JSON. No markdown, no explanations, no extra text.
"""

# ────────────────────────────────────────────────────────────────────────────────
# IMAGE FEEDBACK INTERPRETATION PROMPT
# ────────────────────────────────────────────────────────────────────────────────

INTERPRET_IMAGE_FEEDBACK_PROMPT_V1 = """You are an image editing assistant. Interpret user feedback into structured edits.

CURRENT IMAGE METADATA:
{image_asset_json}

USER FEEDBACK:
"{user_feedback}"

OUTPUT REQUIREMENTS:
Return ONLY a valid JSON object (no markdown, no code fences, no extra text):

{{
  "schema_version": "1.0",
  "edit_delta": {{
    "add_elements": ["string (elements to add)"],
    "remove_elements": ["string (elements to remove)"],
    "modify_elements": [
      {{
        "element": "string (what to modify)",
        "change": "string (how to modify it)"
      }}
    ],
    "style_adjustments": ["string (style changes, e.g., 'more dramatic lighting')"],
    "camera_adjustments": {{
      "angle": "string or null",
      "distance": "string or null (closer/farther)"
    }}
  }},
  "updated_prompt_guidance": "string (brief guidance for building the new prompt)"
}}

INSTRUCTIONS:
- Interpret user feedback into concrete, actionable edits.
- Respect locked attributes (identity, wardrobe, location_layout if preserved).
- Return ONLY the JSON object. No markdown, no explanations, no extra text.
"""

# ────────────────────────────────────────────────────────────────────────────────
# PROMPT BUILDING TEMPLATES
# ────────────────────────────────────────────────────────────────────────────────

BUILD_STYLE_FRAME_PROMPT_V1 = """You are a prompt engineer. Build a style frame generation prompt.

PROJECT BIBLE:
{project_bible_json}

OUTPUT REQUIREMENTS:
Return ONLY a valid JSON object (no markdown, no code fences, no extra text):

{{
  "schema_version": "1.0",
  "prompt": "string (detailed prompt for style frame image generation)",
  "negative_prompt": "string (what to avoid)"
}}

INSTRUCTIONS:
- Generate a prompt that captures the visual style, tone, and aesthetic of the project.
- Include: genre, tone, visual style, color palette, lighting style, aspect ratio.
- Return ONLY the JSON object. No markdown, no explanations, no extra text.
"""

BUILD_CHARACTER_REFERENCE_PROMPT_V1 = """You are a prompt engineer. Build a character reference image generation prompt.

CHARACTER:
{character_json}

PROJECT STYLE:
{style_description}

OUTPUT REQUIREMENTS:
Return ONLY a valid JSON object (no markdown, no code fences, no extra text):

{{
  "schema_version": "1.0",
  "prompt": "string (detailed prompt for character reference image)",
  "negative_prompt": "string (what to avoid)"
}}

INSTRUCTIONS:
- Use character's identity_lock and wardrobe_lock.
- Include project visual style.
- Neutral background, full body or medium shot.
- Return ONLY the JSON object. No markdown, no explanations, no extra text.
"""

BUILD_LOCATION_REFERENCE_PROMPT_V1 = """You are a prompt engineer. Build a location reference image generation prompt.

LOCATION:
{location_json}

PROJECT STYLE:
{style_description}

OUTPUT REQUIREMENTS:
Return ONLY a valid JSON object (no markdown, no code fences, no extra text):

{{
  "schema_version": "1.0",
  "prompt": "string (detailed prompt for location reference image)",
  "negative_prompt": "string (what to avoid)"
}}

INSTRUCTIONS:
- Use location's location_lock, time_of_day, weather.
- Include project visual style.
- Establish layout and atmosphere.
- Return ONLY the JSON object. No markdown, no explanations, no extra text.
"""

BUILD_SHOT_FRAME_PROMPT_V1 = """You are a prompt engineer. Build a shot frame image generation prompt.

SHOT:
{shot_json}

CHARACTERS:
{characters_json}

LOCATION:
{location_json}

PROJECT STYLE:
{style_description}

LOCK PROFILE:
{lock_profile_json}

OUTPUT REQUIREMENTS:
Return ONLY a valid JSON object (no markdown, no code fences, no extra text):

{{
  "schema_version": "1.0",
  "prompt": "string (detailed prompt for shot frame image)",
  "negative_prompt": "string (what to avoid)"
}}

INSTRUCTIONS:
- Start with project style block.
- Include location_lock from location.
- Include identity_lock and wardrobe_lock for each character in shot.
- Include state_in (props held, wardrobe state).
- Include camera setup (shot_type, angle, movement).
- Include action_beats (what's happening in the shot).
- Include continuity_lock verbatim (critical constraints).
- Include negative_prompt from shot.
- Respect lock_profile: if preserve_identity, emphasize identity_lock; if preserve_wardrobe, emphasize wardrobe.
- Include banned_elements in negative_prompt.
- Include must_keep_elements in main prompt.
- Return ONLY the JSON object. No markdown, no explanations, no extra text.
"""
