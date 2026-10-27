# Animated office frontend

The active OfficeCanvas renders lightweight editable SVG furniture and characters. The previous pixel office is retained in LegacyOfficeCanvas.tsx for reference. No backend behavior or model configuration changed as part of this redesign.

Rooms expose existing requirements, discussion, blueprint and agent inspector actions. The six specialists use the existing OfficeContext states. Working and reviewing show typing and monitor activity; discussing moves characters to the meeting area; QA moves to the verification area during TEST or VERIFICATION. Completed and failed states have distinct badges. Artifact arrivals trigger a brief handoff effect. Idle breathing does not imply processing.

Character transitions use corridor waypoints. Walking and typing use CSS; position changes use Framer Motion. Hidden tabs pause ambient animation, and reduced-motion preferences disable ambient effects and character travel. SVG controls support keyboard selection. Small screens hide the team sidebar while keeping agents accessible in the scene.

Zoom and pan are local scene controls. Overview resets both. Existing agent inspection, requirements, blueprint and activity panels remain connected to real backend data. Unsupported pause controls were removed. Failed runs show STOPPED and VS Code remains disabled until verification succeeds.

Validation: TypeScript and Vite production build passed. Browser inspection confirmed distinct character positions, agent inspector content, zoom state changes and no horizontal document overflow at 714px and 1366px widths. A live full pipeline walkthrough remains unverified because the current project stopped on a Gemini provider failure.

Frame sampling: useFrameSample collects 180 requestAnimationFrame intervals without React updates per frame and writes a local data-frame-sample diagnostic on the scene. Hidden tabs report paused. This diagnostic measures local scheduling only; it does not prove 60 FPS on a typical student laptop or under a full active pipeline. No 60 FPS guarantee is claimed.
