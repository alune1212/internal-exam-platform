## ADDED Requirements

### Requirement: Bounded Administrator Invitation Burst Guard
Invitation send and resend actions MUST validate that the target exam exists and is published before allocating in-memory limiter state. The limiter MUST serialize each compound check/update and MUST retain no more than the configured bounded number of keys.

#### Scenario: Administrator targets nonexistent exams
- **WHEN** an authenticated administrator sends invitation actions for arbitrary nonexistent exam IDs
- **THEN** each request fails without allocating a limiter key

#### Scenario: Invitation requests arrive concurrently
- **WHEN** concurrent actions target the same operator, exam, and mode inside one window
- **THEN** the configured per-key limit is applied atomically
- **AND** unique valid keys beyond the global cap evict the oldest limiter state
