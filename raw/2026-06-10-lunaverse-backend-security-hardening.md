# Source: lunaverse-backend production security hardening (2026-06-10)

Session output of the 2026-06-10 security hardening run. Authoritative docs live in the
backend repo: docs/superpowers/specs/2026-06-10-production-security-hardening-design.md
(spec) + docs/superpowers/plans/2026-06-10-production-security-hardening.md (plan) +
docs/security/secret-rotation-2026-06.md (rotation runbook). Merged to main at b8cd95a7.

Key decisions: rotate-not-rewrite for the .env.prod git-history leak (repo private; history
rewrite required before any go-public); Postgres fixed-window rate limiting (prod has no
Redis); CORS allowlist centralized in middleware; prod read-tier cheats are a hard
dependency (deploy smoke + dream-agent callbacks) so the boot assertion enforces
"enabled => strong token + no write tier" instead of "disabled"; leaked Stripe keys
verified TEST-mode.
