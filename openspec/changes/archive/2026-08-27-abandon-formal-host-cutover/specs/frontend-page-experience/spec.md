## ADDED Requirements

### Requirement: Supported macOS Desktop Browsers
The candidate browser self-check SHALL support current macOS Chrome and current macOS Safari in addition to the existing supported Windows, Android, and iOS clients. Embedded browsers, browsers below the documented minimum version, and unrecognized desktop clients MUST remain blocked for formal exams.

#### Scenario: Current macOS Chrome is used
- **WHEN** a candidate opens the formal workflow in Chrome on macOS at or above the documented Chromium minimum
- **THEN** the browser self-check allows the workflow subject to its other device and network checks

#### Scenario: Current macOS Safari is used
- **WHEN** a candidate opens the formal workflow in Safari on macOS at or above the documented Safari minimum
- **THEN** the browser self-check allows the workflow subject to its other device and network checks

#### Scenario: Embedded or obsolete macOS browser is used
- **WHEN** the user agent identifies an embedded browser or a macOS Chrome/Safari version below the documented minimum
- **THEN** the formal workflow is blocked with a supported-browser explanation
