# Environment conventions

- Staging always means Render: https://promop-staging.onrender.com.
- The staging web service is `promop-staging`; its worker is `promop-staging-worker`.
- Do not use the old Google Cloud / Cloud Run staging deployment to investigate or verify staging unless the user explicitly asks for it.
- See `docs/render-staging-celery.md` for Render staging configuration and verification.

# Pull request labels

- When an issue has a security-related label, apply the same label to its pull request.
