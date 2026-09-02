# Exploratory QA Report

# Shipyard Developer Experience QA Report


## Goal completed
YES

## Journey Summary
- Created a new Python project
- Generated an API key
- Inspected the latest deployment logs
- Revisited the API key flow during exploratory review

## Findings

### API key is only shown once without prior warning

**Type:** UX friction  
**Severity:** Medium

**Evidence:**  
The full API key was visible immediately after generation. After navigating away and returning to the API Keys section, only a masked value was available. The interface did not warn the developer that the credential would only be shown once.

**Impact:**  
A first-time developer could navigate away without saving the credential and then be forced to revoke and regenerate it.

## Overall verdict
The primary developer journey can be completed successfully, but the API-key flow creates avoidable friction because an irreversible state change is not clearly communicated.

## State Verification

- Project is in Running state
- Python runtime in Paris region
- 1 active API key created successfully
- Deployment completed successfully (logs showed: Build started → Installing dependencies → Starting application → Server listening on port 8080 → Deployment successful)
- Endpoint available at https://test-python-project.shipyard.dev