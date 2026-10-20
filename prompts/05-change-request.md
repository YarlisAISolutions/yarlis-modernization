# Prompt: change request (new document version)

```markdown
## 1. Role
Act as the requirements owner for [PROJECT].

## 2. Context
See docs/requirements/PROJECT-CONTEXT.md.

## 3. Task
Change request [CR-ID]: [one-sentence change, e.g. "every change to a transaction type is audited: who, when, old/new value"].

## 4. Scope
Documents affected: [BRD | FRD | SRD | RTM]. Carry the change downstream to every affected document.

## 5. Inputs
Requested by [NAME] on [DATE]; reason: [WHY]; references: [LINKS].

## 6. Deliverables
New versions of each affected document (minor bump), with revision rows, snapshots of the previous versions in history/,
and downstream documents re-pinned to the new upstream versions.

## 7. Rules
- Bump first (docver.py bump --level minor --summary "[CR-ID]: ..." --sections "..." --author "[NAME]"), then edit.
- Edit only the affected sections; new IDs take the next free number; nothing is renumbered.
- Update downstream documents and bump them with --refresh-upstream; run rtm sync if an RTM exists.
- Decisions the change needs and you can't make go to open questions with an owner.

## 8. Verification and report
Run linkify, trace --inject, validate and diff. Report old → new version per document, the sections changed (they must match
the revision row), the IDs added or retired, and the open questions.
```
