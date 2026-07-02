## Why

The platform needs a standalone learning surface where internal exam takers can watch uploaded training videos and administrators can verify whether each video was completed. This solves a training-completion tracking gap without coupling learning progress to exam eligibility, exam scoring, ranking, or retake behavior.

## What Changes

- Add a standalone video learning capability for locally uploaded training videos.
- Allow administrators to upload, publish, archive, list, and update basic video metadata.
- Store uploaded video files on local application storage with bounded upload validation and stable server-generated storage keys.
- Expose published videos to authenticated active candidates through candidate-token-gated learning APIs.
- Track candidate video watch progress independently from exams and mark a video complete when the candidate has watched at least 90% of the video duration.
- Add candidate-facing learning pages for video listing, playback, progress display, and completion state.
- Add administrator-facing learning pages and reports for video inventory and candidate completion status.
- Keep video learning independent from exam configuration, active exam discovery, exam start, attempt snapshots, scoring, ranking, and retake grants.
- Non-goals: no full LMS course hierarchy, no live streaming, no DRM or screen-recording prevention, no anti-cheat suite, no background transcoding queue, no SCORM/xAPI, no complex RBAC, and no requirement that learning completion unlocks exams.

## Capabilities

### New Capabilities

- `video-learning`: Standalone local video upload, candidate playback, 90% completion tracking, and administrator learning completion reporting.

### Modified Capabilities

- None.

## Impact

- Backend: new SQLAlchemy models, Alembic migration, Pydantic schemas, learning API routes, learning services, local upload storage configuration, and upload/progress/report tests.
- Frontend: new candidate learning routes/pages, admin learning routes/pages, API client functions, query keys, navigation entries, and page-state tests using the existing Academic Editorial design system.
- Deployment: Docker Compose and Nginx need a local uploaded-media volume and static media serving path sized for video uploads; upload size limits must be aligned across backend, frontend messaging, and Nginx.
- Security and operations: uploaded file validation, safe generated storage keys, candidate/admin token protection, non-public metadata APIs, and documented storage backup/retention expectations.
