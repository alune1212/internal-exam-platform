# Candidate Access Specification

## Purpose

Candidate access covers candidate login, candidate-scoped exam discovery, and practice API access.

## Requirements

### Requirement: Candidate Login
The system SHALL authenticate candidates with name, phone suffix, and optional employee number before issuing a candidate token.

#### Scenario: Candidate logs in with matching identity
- **GIVEN** an active candidate record exists
- **WHEN** the candidate submits matching name and phone suffix, with a matching employee number when provided
- **THEN** the system returns a signed candidate token

#### Scenario: Candidate identity does not match
- **GIVEN** no active candidate record matches the submitted identity
- **WHEN** the candidate submits the login form
- **THEN** the system rejects the login without issuing a candidate token

### Requirement: Candidate-Scoped Active Exams
The system SHALL require X-Candidate-Token for active exam listing and SHALL only return active exams in the candidate's exam scope that the candidate can still enter.

#### Scenario: Candidate has an eligible active exam
- **GIVEN** a valid candidate token and an active exam containing the candidate in exam_candidate_scope
- **WHEN** the candidate requests active exams
- **THEN** the response includes that exam with server-calculated availability status

#### Scenario: Candidate already submitted without retake grant
- **GIVEN** a candidate has submitted an exam and has no unused retake grant
- **WHEN** the candidate requests active exams
- **THEN** the submitted exam is excluded from the active exam list

### Requirement: Practice API Privacy
The system MUST require X-Candidate-Token for practice APIs and MUST NOT expose correct answers, analysis, correctness, or score in practice question or submit responses.

#### Scenario: Candidate lists practice questions
- **GIVEN** a valid candidate token
- **WHEN** the candidate requests practice questions
- **THEN** the response omits correct answers and analysis

#### Scenario: Candidate submits practice answer
- **GIVEN** a valid candidate token
- **WHEN** the candidate submits a practice answer
- **THEN** the response omits correct answer, analysis, correctness, and score while the server may persist practice result data
