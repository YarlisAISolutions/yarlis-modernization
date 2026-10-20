---
description: Apply a change request to a feature's requirements with version bumps carried downstream
agent: agent
argument-hint: feature=<module/feature> change=<one sentence> requester=<name>
---

Use the `requirements-docs` skill. Follow [prompts/05-change-request.md](../../prompts/05-change-request.md).

- Feature folder: docs/requirements/${input:feature:module/feature, e.g. accounts/account-update}/
- Change: ${input:change:the change in one sentence}
- Requested by: ${input:requester:name or role}

For each affected document, in BRD → FRD → SRD → RTM order: run `docver.py bump <doc> --level minor --summary "<CR>: …" --sections "…" --author "<requester>"`
first (downstream documents also get `--refresh-upstream`), then edit only the affected sections. New IDs take the next free number.
Finish with linkify, trace --inject, rtm sync (if there's an RTM), validate, diff and `index docs/requirements`. Report old → new versions,
sections changed, IDs added or retired, and open questions.
