# Legacy Contract Inventory

This inventory was captured from commit `d6c65bd` before the account migration was applied. It is an implementation checklist, not a runtime contract. The source command was:

```bash
git grep -n -E 'employee_no|phone_suffix|should_attend|is_login_sentinel' HEAD -- \
  ':!backend/alembic/versions/*' ':!openspec/changes/archive/*'
```

## Runtime And API

| Area | Baseline references that must be removed or replaced |
| --- | --- |
| Candidate login | `backend/app/api/candidates.py`, `backend/app/schemas/candidate.py`, and `backend/app/services/candidate_service.py` accepted or matched name, employee number, phone suffix, and sentinel identity. |
| Candidate persistence | `backend/app/models/candidate.py` stored employee number, phone suffix, global attendance, global organization/personnel data, and the login sentinel flag. |
| Exam authorization | `backend/app/services/exam_attempts.py`, `exam_configuration.py`, and `exam_service.py` used global `should_attend` and mutable candidate identity. These checks must become active-account plus exam-scope checks. |
| Import/template routes | `backend/app/api/imports.py`, `import_service.py`, and `template_service.py` exposed the standalone candidate template/service. The exam-roster route remains, but its workbook becomes email keyed. |
| Reports and learning | `backend/app/schemas/{report,learning}.py` and `backend/app/services/{report,learning}_service.py` exposed employee/global identity. Formal reports must use frozen scope snapshots; learning reports use account identity. |
| Operations | `backend/app/ops/e2e_seed.py` and `capacity_gate.py` seeded employee number and global attendance. |

## Frontend And Visible Contracts

| Area | Baseline references that must be removed or replaced |
| --- | --- |
| Candidate authentication/session | `frontend/src/api/auth.ts`, `types/candidate.ts`, `lib/candidateSession.ts`, `pages/LoginPage.tsx`, and layout/name-plate code exposed legacy identity fields. |
| Candidate exam pages | `frontend/src/pages/ExamStartPage.tsx` displayed employee number and relied on the legacy candidate shape. |
| Admin roster/import | `frontend/src/pages/admin/ExamCandidatesPage.tsx`, candidate import pages, and `frontend/src/types/{exam,imports}.ts` used legacy columns. |
| Reporting | Admin score, absence, and learning report pages/types rendered employee or global attendance fields. |
| Tests | Candidate, layout, page, admin, report, learning, and client fixtures under `frontend/src/**/*.test.ts?(x)` encoded the old response shape. |

## Documentation And OpenSpec Baseline

- `docs/api-design.md`, `docs/database-design.md`, `docs/import-templates.md`, and `docs/handoff.md` documented roster-bound login, the sentinel, employee/name matching, and the standalone candidate template.
- Root and active OpenSpec baselines may still mention the old early-login window or candidate import contract until task 12.7 rebases them. Archived changes remain immutable evidence and are not current runtime contracts.

## Standalone Import Surface To Retire

- `GET /api/admin/imports/templates/candidates`
- `generate_candidate_template()`
- `import_candidates_from_workbook()`

`POST /api/admin/exams/{exam_id}/candidates/import` is not retired; it becomes the reduced email-keyed exam-roster import.

## Audit-Only Exceptions

The following may retain literal legacy field names after implementation:

- immutable Alembic revisions that describe the historical schema;
- the new account-migration preflight and its focused migration fixtures, where the names are required to detect or migrate old data;
- this inventory and archived OpenSpec history.

Current models, schemas, routes, services, seeds, user-facing documentation, frontend source, ordinary tests, API responses, workbook headers, and exports are not exceptions.
