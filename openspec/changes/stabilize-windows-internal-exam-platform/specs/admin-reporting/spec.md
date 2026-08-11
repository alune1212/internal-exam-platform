## MODIFIED Requirements

### Requirement: Ranking Uses Submitted Results
The system SHALL calculate administrator-only rankings from submitted or auto-submitted formal attempt results and MUST exclude voided attempts. Candidate-facing APIs and pages MUST NOT expose ranking.

#### Scenario: Administrator requests ranking
- **GIVEN** candidates have submitted or auto-submitted attempts for an exam
- **WHEN** an authenticated operator requests ranking through the loopback admin surface
- **THEN** the ranking reflects persisted eligible attempt scores for that exam
- **AND** excludes voided attempts

#### Scenario: Candidate requests ranking
- **WHEN** a candidate or unauthenticated LAN client requests ranking
- **THEN** the system rejects the request or omits candidate-ranking behavior

## ADDED Requirements

### Requirement: Voided Attempt Reporting
Normal score, accuracy, wrong-question, pass-rate, attendance-completion, ranking, and export aggregates MUST exclude voided attempts. Administrator incident views and evidence exports SHALL retain voided attempt identity, timing, reason, operator, and retake outcome.

#### Scenario: Normal report includes an exam with voided attempts
- **WHEN** an authenticated operator opens or exports a normal exam report
- **THEN** voided attempt scores and answers do not contribute to normal aggregates
- **AND** normal status does not represent a voided attempt as a completed valid result

#### Scenario: Operator opens incident outcomes
- **WHEN** an authenticated operator views the affected exam's incident report
- **THEN** voided attempts and bulk-retake outcomes are visible with their persisted reasons and timestamps
- **AND** the view contains no secret or OTP data

### Requirement: Formal Exam Evidence Bundle
The system SHALL generate a checksummed non-secret evidence bundle for each formal exam containing release/configuration facts, publication and preflight outcomes, roster and pool summaries, SMTP verification, lifecycle timestamps, incident/retake events, backup identifiers, and close-exam results.

#### Scenario: Formal exam closes normally
- **WHEN** the operator completes the guarded close-exam workflow
- **THEN** the evidence bundle records the accepted release, preflight, exam timing, outcome summary, backup references, and session invalidation result

#### Scenario: Formal exam has an incident
- **WHEN** attempts are voided or bulk retakes are granted
- **THEN** the evidence bundle includes the incident audit references and row-level outcome artifact
- **AND** excludes passwords, token values, OTPs, and full sensitive configuration
