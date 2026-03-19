# Collaboration Notes

## Purpose

Shared working notes for Codex and AG during refactoring passes.

## How To Use

- Add a dated section per pass
- Capture decisions, blockers, and open questions
- Keep entries short and factual
- Do not store secrets here

## Current Baseline

- Git cleanup pass in progress
- Local/generated files are being removed from version control
- Next step after cleanup: stabilize settings, local dev flow, and deployment config

## Template

### Pass: YYYY-MM-DD - short title

- Goal:
- Changes made:
- Risks found:
- Questions:
- Next step:


### Pass: 2026-03-19 - Plan Alignment (AG + Codex)

- **Goal:** Align on Testing, Roadmap, CI/CD, and Local Settings.
- **Decisions Provided by User:**
  1. **Testing:** There are no existing unit tests. The user will provide an `.xlsx` input dataset in the root directory. **Codex's Task:** Write a test script/routine in the repository capable of reading this `.xlsx` file, passing it to the optimizer, and validating the output. This must be done to baseline the DP engine before deep refactoring.
  2. **Algorithm Roadmap:** We will focus *exclusively* on cleaning and modularizing the existing DP algorithm in this pass. Global optimization (GA/Local Search) will be a separate R&D phase later.
  3. **CI/CD:** Keep it extremely simple. Workflow: Commit to GitHub (`kaushikray0601/opti_api.git`) locally $\rightarrow$ SSH into Oracle Cloud $\rightarrow$ `git pull` $\rightarrow$ deploy via docker-compose. No complex GitHub Actions are needed for MVP.
  4. **Local Dev Cookies:** **Codex's Task:** Update `settings.py` so that security settings like `CSRF_COOKIE_SECURE` and `SESSION_COOKIE_SECURE` are dynamically set to `False` when `ENV_MODE=dev` or `DEBUG=True`. This will unblock local non-HTTPS testing.
- **Next step:** Codex to implement the `.xlsx` baseline test, update `settings.py`, and begin the DP engine modularization. AG to peer-review the pull requests/commits.
