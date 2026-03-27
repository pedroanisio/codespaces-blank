Propose a comprehensive, extensible JSON-based data schema (preferably defined as a JSON Schema) that enables programmatic creation, storage, management, versioning, and orchestration of all assets required to generate and assemble high-quality videos up to 30 minutes in length.

The schema must:
- Be fully tool-agnostic and extensible to support **any** current or future generative-AI tools and pipelines (e.g., Runway, Kling, Luma Dream Machine, Pika, Midjourney, ElevenLabs, Stable Diffusion, or any new model/API) without modification.
- Support programmatic video assembly and post-production scripts using the following Python libraries: MoviePy, Movis, OpenCV, PyAV, and Manim.
- Define a clear hierarchical and relational structure covering these core asset types:
  - Story / narrative arc
  - Full script (including dialogue, action descriptions, and timing)
  - Director’s instructions / creative direction
  - Scenes and individual shots (with detailed visual, technical, and stylistic specifications)
  - Visual assets (images, storyboards, character references, environment references)
  - Audio assets (voice-over, music, sound effects, with synchronization metadata)
  - Marketing materials (trailers, thumbnails, promotional stills, social-media clips)
  - Final video outputs (including versioned renders and assembly instructions)
- Include explicit, extensible fields for measurable high-quality video specifications at both project and asset levels, such as:
  - Resolution (e.g., 4K, 1080p, 720p, or custom)
  - Temporal consistency requirements
  - Character coherence across shots
  - Cinematic lighting and style guidelines
  - Aspect ratios (e.g., 16:9, 9:16, 2.35:1, or custom)
  - Frame rates (e.g., 24 fps, 30 fps, 60 fps, or custom)
  - Any additional quality controls (color grading, motion blur, etc.)
- Provide detailed generative-AI parameters on every relevant asset (prompts, negative prompts, model/version identifiers, seed values, consistency anchors such as character/style references or IP adapters, etc.).
- Define clear relationships, dependencies, and versioning rules between assets so they can be programmatically composed, validated, and rendered into a coherent final video.

Present the schema as an entity-relationship description or full JSON Schema definition. **Do not provide any code implementation.**
