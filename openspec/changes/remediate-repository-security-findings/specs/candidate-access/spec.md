## MODIFIED Requirements

### Requirement: Practice API Privacy
The system MUST require `X-Candidate-Token` from an active account for practice APIs and MUST use the same shared active question bank that formal exams draw from. Practice question responses MUST omit correct answers and analysis before submission. After an authenticated candidate submits one bounded answer, the response SHALL reveal that submission's correctness, normalized correct answer, analysis, and selected-versus-correct option comparison. Each accepted submission MUST remain immutable, update the account-question all-time aggregate in the same transaction, and be subject to the documented per-account candidate rate limit (`include_client_ip=False`) and hot-history ceiling.

#### Scenario: Candidate lists practice questions
- **GIVEN** a valid candidate token for an active account
- **WHEN** the candidate requests practice questions
- **THEN** the response draws from the shared active question bank
- **AND** it omits correct answers and analysis

#### Scenario: Candidate submits practice answer
- **GIVEN** a valid candidate token, an active practice question, and available hot-history capacity
- **WHEN** the candidate submits an answer within the documented length and per-account rate limit
- **THEN** the system persists one immutable practice result and atomically updates its all-time aggregate
- **AND** the response returns correctness, the normalized correct answer, analysis, and option comparison

#### Scenario: Candidate changes an already submitted practice answer
- **GIVEN** a practice result has already been returned for one submission
- **WHEN** the candidate answers that question again within the documented boundaries
- **THEN** the system creates a new immutable practice-answer record rather than modifying the prior result
- **AND** atomically advances the all-time aggregate to the latest result

#### Scenario: Candidate exceeds a practice boundary
- **WHEN** an answer exceeds the supported length, the per-account submission rate is exceeded, or the account has reached the hot-history ceiling
- **THEN** the system rejects the submission with the documented validation, rate-limit, or conflict response
- **AND** it persists neither a detail row nor a partial aggregate update

### Requirement: Wrong-Question Review
The system SHALL provide each authenticated active account with a paginated wrong-question review derived only from that account's practice aggregates and retained detail over the shared question bank. Review results MUST support the existing category and mastered-state filters, stable latest-activity ordering, a non-negative offset no greater than 2^31-1, bounded recent-history detail, the existing per-account candidate rate limit (`include_client_ip=False`), and all-time attempt/error counts without exposing another account's history. The rate limit MUST be applied before the aggregate/history query.

#### Scenario: Candidate reviews incorrect practice
- **GIVEN** an active account has an all-time aggregate with at least one incorrect submission
- **WHEN** the candidate requests a bounded wrong-question page
- **THEN** the system returns only the requested page in stable latest-activity order
- **AND** it returns at most the requested recent-history count with total/truncated metadata
- **AND** it does not expose another account's practice history

#### Scenario: Candidate later answers correctly
- **GIVEN** an earlier incorrect practice submission exists
- **WHEN** a later practice submission for the same question is correct
- **THEN** the aggregate and current review show the item as mastered
- **AND** all-time attempt and error counts do not decrease when old detail is archived

#### Scenario: Candidate sends an oversized or repeated wrong-question request
- **GIVEN** a valid candidate token
- **WHEN** the candidate supplies an offset above 2^31-1 or exceeds the existing per-account candidate rate limit
- **THEN** the system returns the stable validation or rate-limit response before executing the wrong-question query

## ADDED Requirements

### Requirement: Scope Before Exam State Disclosure
Candidate exam start MUST verify the current account's per-exam scope before disclosing examination state. Missing and unassigned examinations MUST use the same not-found response. An assigned active account MUST retain the existing lifecycle, time-window, and read-only attempt recovery behavior.

#### Scenario: Uninvited account probes examination IDs
- **WHEN** an active account starts a missing, draft, archived, or active examination outside its scope
- **THEN** it receives the same not-found status and message shape without learning the examination state

### Requirement: Rate Limit Before Candidate Mutation Locks
Every authenticated candidate mutation endpoint, including practice submission, exam start, attempt answer save/submit/takeover, learning progress, and profile mutation, MUST apply the existing per-account candidate rate limit (`include_client_ip=False`) before acquiring advisory or row locks. Read-only attempt retrieval MUST avoid mutation row locks. Public candidate login and OTP endpoints retain their existing IP-and-identifier rate limits.

The shared in-process limiter MUST serialize pruning, quota checks, admission, and key eviction so concurrent threads cannot over-admit a retained bucket or corrupt its bounded key state. This process-local burst guard does not replace persisted OTP quotas.

#### Scenario: Candidate mutation arrives under exhausted quota and lock contention
- **GIVEN** a valid candidate token whose per-account mutation quota is exhausted and a candidate or advisory lock is contended
- **WHEN** the candidate invokes any supported mutation endpoint
- **THEN** the system returns the stable rate-limit response before acquiring the lock or changing data

#### Scenario: Candidate retrieves an attempt read-only
- **WHEN** an authenticated candidate retrieves an attempt without mutating it
- **THEN** the system reads the attempt without a mutation row lock

#### Scenario: Concurrent requests share a retained limiter bucket
- **WHEN** concurrent threads submit requests within one quota window
- **THEN** accepted requests do not exceed the configured bucket quota
- **AND** key churn stays bounded without concurrent-mutation errors

### Requirement: Guarded Practice Detail Retention
The system MUST keep at most 5000 hot practice-answer detail rows per account and treat details older than 365 days as archive candidates. Archival deletion MUST be an explicit administrator operation that preserves all-time aggregate state and reduces a capacity-blocked account to 4000 hot rows.

#### Scenario: Account reaches hot-history capacity
- **GIVEN** an account has 5000 retained practice-answer detail rows
- **WHEN** it attempts another practice submission
- **THEN** the system returns a stable conflict response until an administrator completes guarded archival deletion

#### Scenario: Archived details are deleted safely
- **GIVEN** an archive exactly binds eligible detail rows and a later paired backup has passed validation
- **WHEN** an administrator confirms deletion against an unchanged preview fingerprint
- **THEN** the system deletes only the archived detail identifiers
- **AND** preserves the account-question aggregate and unarchived hot rows

### Requirement: Bounded Candidate Exam Answer Saves
Candidate exam answer-save requests MUST use bounded positive attempt-question identifiers, a maximum selected-answer length of 32 characters, at most 5000 answer items, and a non-negative 32-bit answer revision. The service MUST reject duplicate question identifiers and payloads that exceed the persisted questions in the attempt before mutating answers or the attempt revision.

#### Scenario: Candidate submits an oversized or malformed answer payload
- **GIVEN** an active candidate attempt
- **WHEN** the candidate submits an answer payload with an invalid identifier, overlong answer, too many items, duplicate question identifier, out-of-range revision, or more items than the attempt contains
- **THEN** the system returns a stable validation response before persisting any answer or revision change

### Requirement: Bounded Practice Catalog Reads
Authenticated practice-catalog reads MUST use stable ID-ordered pagination with a page size no greater than 100 and a non-negative 32-bit offset, MUST recheck active status when loading the selected page, and MUST apply the existing per-account candidate rate limit (`include_client_ip=False`) before querying the active question catalog.

#### Scenario: Candidate reads the practice catalog in pages
- **GIVEN** a valid candidate token for an active account
- **WHEN** the candidate requests a practice page with a valid limit and offset
- **THEN** the system returns no more than 100 active questions in stable ID order
- **AND** the query loads only the requested page and its required options

#### Scenario: Candidate exceeds the practice catalog rate limit
- **GIVEN** a valid candidate token for an active account
- **WHEN** repeated catalog requests exceed the existing per-account candidate rate limit
- **THEN** the system returns the stable rate-limit response before loading the question catalog
