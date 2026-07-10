# Contributing to AquaSense

Thank you for your interest in contributing to AquaSense! As a developer on this project, please adhere to the following workflow, coding standards, and Git conventions to ensure codebase consistency and operational stability.

---

## 📜 Codebase Standards

All changes should respect our structural guidelines:
1. **Layered Architecture:** Clear separation of API, Services, Repositories, ML, Ingestion, and Core layers. No layer should bypass its adjacent layers.
2. **Code Style:** Follow language-idiomatic standards (e.g., PEP 8 for Python, standard styling for TypeScript/React). Keep functions concise and single-responsibility.
3. **Security Principles:** Never hardcode secrets. All inputs arriving from client APIs or physical IoT devices must be strictly validated.
4. **Data Isolation:** Keep database queries inside the repository modules.

---

## 🌿 Branching Strategy

We follow a structured branch naming convention. Create branches off the `main` branch:

* **Features:** `feature/your-feature-name` (e.g. `feature/ml-retraining-endpoint`)
* **Bug Fixes:** `fix/short-bug-description` (e.g. `fix/sse-disconnection-leak`)
* **Documentation:** `docs/update-description` (e.g. `docs/add-esp32-schematic`)
* **Refactoring:** `refactor/refactor-name` (e.g. `refactor/consolidate-migrations`)

---

## 💬 Commit Message Convention

We enforce the **Conventional Commits** specification. Commits should look like this:

`type(scope): description`

### Supported Types:
* `feat`: A new feature (e.g. `feat(ml): add SHAP Tree explainer`)
* `fix`: A bug fix (e.g. `fix(auth): clear cookies on logout fail`)
* `docs`: Documentation updates only (e.g. `docs(api): document SSE events`)
* `style`: Code style adjustments (white-space, formatting, semicolons - no logic changes)
* `refactor`: Code restructuring that neither fixes a bug nor adds a feature (e.g. `refactor(db): consolidate SQL migrations`)
* `test`: Adding or correcting tests (e.g. `test(wqi): add WQI scoring edge cases`)
* `chore`: Tooling, configs, or dependency updates (e.g. `chore(deps): upgrade pytest`)

---

## 🛠 Pre-PR Checklist

Before opening a Pull Request (PR), verify that your code compiles and passes all checks:

### 1. Run Python Tests
Ensure the python environment is configured correctly, then run:
```bash
backend\.venv\Scripts\python -m pytest
```
*All tests must pass (100% green).*

### 2. Validate Frontend Compilations & Linting
From the `/frontend` directory, run:
```bash
# Verify Next.js production build succeeds
npm run build
```

### 3. Check for Committed Secrets
Perform a scan to confirm no `.env` file, secret token, or active API key is committed. Keep placeholders in `.env.example`.
