# Contributing to AquaSense

Welcome! As a developer on the AquaSense project, please adhere to the following workflow, coding styles, and git conventions to ensure codebase consistency and operational stability.

---

## 📜 Engineering Standards (The Constitution)

Our development is strictly governed by the **AquaSense Engineering Constitution** located in [.agents/rules/constitution.md](file:///.agents/rules/constitution.md). 

All changes must respect:
1.  **Layered Architecture:** The separation of API, Services, Repositories, ML, Ingestion, and Core layers. No layer may cross over its neighbor.
2.  **Code Shape:** Cap functions at 40-60 lines, and keep source files under 300 lines where possible.
3.  **Security Gates:** No secrets are ever hardcoded. All inputs arriving from client APIs or physical IoT devices must be strictly type and range validated via Pydantic or parsing helpers.
4.  **No Direct DB queries in APIs:** Keep direct Supabase client executions and SQL queries inside the `/repositories` folder.

---

## 🌿 Branching Strategy

We follow a structured branch naming convention. Create branches off the `main` branch:

*   **Features:** `feature/your-feature-name` (e.g. `feature/ml-retaining-endpoint`)
*   **Bug Fixes:** `fix/short-bug-description` (e.g. `fix/sse-disconnection-leak`)
*   **Documentation:** `docs/update-description` (e.g. `docs/add-esp32-schematic`)
*   **Refactoring:** `refactor/refactor-name` (e.g. `refactor/consolidate-migrations`)

---

## 💬 Commit Message Convention

We enforce the **Conventional Commits** specification. Commits should look like this:

`type(scope): description`

### Supported Types:
*   `feat`: A new feature (e.g. `feat(ml): add SHAP Tree explainer`)
*   `fix`: A bug fix (e.g. `fix(auth): clear cookies on logout fail`)
*   `docs`: Documentation updates only (e.g. `docs(api): document SSE events`)
*   `style`: Code style adjustments (white-space, formatting, semicolons - no logic changes)
*   `refactor`: Code restructuring that neither fixes a bug nor adds a feature (e.g. `refactor(db): consolidate SQL migrations`)
*   `test`: Adding or correcting tests (e.g. `test(wqi): add WQI scoring edge cases`)
*   `chore`: Tooling, configs, or dependency updates (e.g. `chore(deps): upgrade pytest`)

---

## 🛠 Pre-PR Checklist

Before opening a Pull Request (PR), verify that your code compiles and passes all checks:

### 1. Run Backend Tests
Ensure the backend virtual environment is active, then run:
```bash
pytest
```
*All tests must pass (100% green).*

### 2. Validate Frontend Compilations & Linting
From the `/frontend` directory, run:
```bash
# Verify ESLint passes without errors
npm run lint

# Verify Next.js production build succeeds
npm run build
```

### 3. Check for Committed Secrets
Perform a manual scan or run git tools to confirm no `.env` file, secret token, or active API key is committed. Keep placeholders in `.env.example`.

### 4. Architectural Decisions & Diagrams
*   If you introduced a new architectural approach or design trade-off, write an ADR inside [docs/adr/](file:///D:/Coding%20Projects/College%20Era/AquaSense/docs/adr/) following the contextual structure (Context -> Decision -> Consequences).
*   If layer boundaries changed, update the Mermaid sequence and flowcharts in [docs/diagrams/architecture.md](file:///D:/Coding%20Projects/College%20Era/AquaSense/docs/diagrams/architecture.md).
