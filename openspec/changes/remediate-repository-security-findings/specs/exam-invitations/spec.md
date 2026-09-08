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

### Requirement: Freeze-Aware Background Invitation Delivery
Background invitation delivery MUST reacquire the shared backup/write fence in its delivery session before mutating invitation scope state. If the fence is unavailable, delivery MUST roll back its mutation and retain the claim for a later retry; after the fence is released, delivery MAY commit normally.

#### Scenario: Delivery runs during a writer freeze
- **GIVEN** an invitation claim has been acquired and the shared backup or writer fence is held
- **WHEN** the background delivery worker attempts to update the invitation scope
- **THEN** the delivery transaction is rejected and rolled back before changing scope state
- **AND** the claim remains available for retry

#### Scenario: Delivery runs after the freeze is released
- **GIVEN** an invitation claim has been acquired and no writer or backup freeze is held
- **WHEN** the background delivery worker performs its guarded update
- **THEN** it commits the delivery state normally
