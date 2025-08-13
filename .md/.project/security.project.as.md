```markdown
# Security Policy for memos.as

Version: 1.1

Parent Policy: DevEnviro Security Policy

This document outlines security considerations and policies specific to the memos.as service. It inherits all policies from the main devenviro.as/security.project.md file.

## 1. Reporting a Vulnerability

Please follow the main DevEnviro policy for reporting vulnerabilities. Do not report security issues through public GitHub issues.

## 2. Scope

This policy applies specifically to the memos.as codebase and its corresponding Docker image.

## 3. Service-Specific Security Considerations

### Data in Transit

*   All communication between services occurs over the internal Docker network. Production deployments **must** configure TLS/SSL for all inter-service communication.

### Data at Rest

*   **Episodic Memory (Qdrant):** May contain sensitive information from source documents or tasks. Access to the Qdrant database must be strictly controlled.
*   **Tool Registry (PostgreSQL):** Contains endpoint URLs and API schemas critical to the ecosystem's function and must be protected from unauthorized modification.

### API Endpoint Security

*   The API endpoints for memos.as are designed for internal service-to-service communication only and should not be exposed to the public internet.
*   Production environments **must** implement API authentication (e.g., API key or JWT) to ensure only authorized services can access memory and tool functions.

### Local Model Security (LM Studio)

*   **Model Provenance:** The Cortex Agent will be downloading and executing models from community sources like Hugging Face. It is a critical security principle that **all models must be vetted** before being used in a production or sensitive environment. Only download models from trusted publishers (e.g., Mistral AI, Microsoft, Google, Qwen).
*   **Resource Management:** While not a traditional security vulnerability, poorly configured models can lead to denial-of-service conditions on the local machine. Resource limits and monitoring should be in place. 
```