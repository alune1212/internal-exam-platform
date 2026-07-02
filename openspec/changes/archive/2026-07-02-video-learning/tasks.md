## 1. Persistence And Storage

- [x] 1.1 Add `learning_video` and `learning_video_progress` SQLAlchemy models with relationships to `Candidate` where needed.
- [x] 1.2 Add an Alembic migration for learning video metadata, candidate progress, uniqueness constraints, and useful report indexes.
- [x] 1.3 Add backend settings for learning media storage directory, public media path, allowed video content types, and default 500 MiB max upload size.
- [x] 1.4 Add a local storage helper that writes uploads through generated storage keys, rejects unsafe filenames/types/sizes, and avoids storing user filenames as paths.
- [x] 1.5 Update Docker Compose and Nginx configuration to mount the learning media directory and serve uploaded videos through the 8080 entrypoint with matching upload-size limits.

## 2. Backend Learning APIs

- [x] 2.1 Add Pydantic schemas for admin video metadata, upload/update responses, candidate video reads, progress updates, and learning report rows.
- [x] 2.2 Add a `learning_service` for admin upload/list/update/publish/archive behavior, keeping route files thin.
- [x] 2.3 Add admin learning routes protected by `X-Admin-Token` for video upload, list, detail/update, publish, archive, report, and report export.
- [x] 2.4 Add candidate learning routes protected by `X-Candidate-Token` for published video list, video detail, and progress heartbeat.
- [x] 2.5 Implement watched-interval merge logic so seek jumps and repeated intervals do not inflate progress toward the 90 percent completion threshold.
- [x] 2.6 Add backend tests for upload validation, generated storage keys, status visibility, candidate auth/inactive rejection, progress completion, seek/double-count prevention, and report/export behavior.
- [x] 2.7 Add regression tests proving incomplete learning progress does not block active exam listing or exam start and completed learning does not affect exam scoring/ranking/practice behavior.

## 3. Candidate Frontend

- [x] 3.1 Add frontend learning types, API client functions, and candidate query keys under the existing API/query-key structure.
- [x] 3.2 Add candidate routes and top navigation entry for `/learning` and `/learning/:videoId` without changing existing exam/practice routes.
- [x] 3.3 Build the candidate learning list page with loading, empty, error, progress, and completed states using existing page primitives.
- [x] 3.4 Build the candidate video player page with native video controls, metadata loading, progress display, resume position, heartbeat updates, and completion feedback.
- [x] 3.5 Add focused frontend tests for candidate learning query gating, archived-video omission, playback progress UI, completion state, and no-session redirect behavior.

## 4. Admin Frontend

- [x] 4.1 Add admin learning types, API client functions, query keys, and side-rail navigation entry.
- [x] 4.2 Build the admin video list and upload/edit surfaces with product-styled file selection, client-side duration extraction, status actions, and upload error states.
- [x] 4.3 Build the admin learning report page with video/status filters, table states, completion labels, and Excel export action.
- [x] 4.4 Add focused frontend tests for upload validation UI, duration capture, publish/archive actions, report filters, export action, and responsive navigation.

## 5. Documentation And Verification

- [x] 5.1 Update `docs/api-design.md`, `docs/database-design.md`, `docs/requirements.md`, `docs/handoff.md`, and environment/deployment docs for video learning, local media storage, upload limits, and backup expectations.
- [x] 5.2 Run backend checks: `uv run ruff format . --check`, `uv run ruff check .`, `uv run ty check`, `uv run pytest`, and Alembic upgrade verification.
- [x] 5.3 Run frontend checks: `npm run format:check`, `npm test -- --run`, `npm run lint`, and `npm run build`.
- [x] 5.4 Run deployment checks: `docker compose --env-file .env config`, Compose/Nginx rebuild smoke, `nginx -t`, `/api/health`, `/docs`, and a browser smoke through `http://127.0.0.1:8080` for candidate/admin learning pages.
- [x] 5.5 Run `openspec validate video-learning --type change --strict` before implementation is considered ready.
