# Security review policy

Independent review is mandatory when **either**:

- A PR changes a security-sensitive file (including renaming one away).
- The PR, a closing issue, or an issue referenced in its title/body has a
  `security` label. Case-insensitive `security:` and `security-` labels also count.

Security files include authentication, authorization, OAuth, session settings,
identity providers, security middleware, CI/review policy, security scan baselines,
dependencies, environment/deployment configuration, and security documentation.
The exact patterns and test-file exclusions are in
`.github/scripts/security-review.cjs`. Test-only changes do not trigger review
based on paths, but a security label still requires approval.

An approval must cover the current head commit and come from someone with write
access who is neither the PR author nor the current commit's author/committer.
Dismissed approvals, old-commit approvals, and outstanding requested changes do
not satisfy the check. Native file rules require a member of the existing
`healthkey` team and dismiss approvals when new reviewable commits are pushed.

PRs outside these categories can merge without an approving review. Required
backend/frontend/security CI checks, signed commits, linear history, PRs, resolved
review threads, and force-push protection remain in place.

## Enforcement and rollout

The repository ruleset `main-protection` applies to `dev` and `main`:

- Global approval count: zero; global last-push approval: disabled.
- Native file-scoped reviewer: one approval from `healthkey` for the configured
  security paths. GitHub limits this native list to 15 patterns; the status check
  covers the complete file list and issue/PR labels.
- Required status context: `Security review`, in addition to the existing three
  CI contexts. Add this context only after the policy workflow is on the trusted
  default branch and has successfully published statuses for existing PRs.

The policy workflow runs trusted default-branch code with read-only metadata
permissions plus permission to write commit statuses. It never checks out PR code.
A separate, unprivileged review-event workflow only signals `workflow_run` so
approval/dismissal events are evaluated by trusted code. PR and issue changes also
trigger checks. A five-minute schedule reconciles missed events and labels on
issues in other repositories; scheduled GitHub Actions can be delayed.

API failures fail closed. PRs sharing the same head commit are evaluated together
so a non-security PR cannot overwrite a security PR's failed status. Newly pushed
commits need their own check and fresh approval.

Policy/workflow changes are themselves security-sensitive and require review.
The label check is not active until its workflow is merged and the required status
context is enabled; the native file rule can be applied separately.

## Validation

Run `node --test .github/scripts/security-review.test.cjs`. Tests cover file and
label triggers, linked issues, independent/current approvals, dismissals,
requested changes, API errors, and test-only changes.
