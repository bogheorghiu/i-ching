# Keep personal data out of the repository, every branch and every commit

(No `paths:` on purpose: any edit can carry personal data, so this loads in every session.)

The repository is public, and a name committed once stays in its history after the file is fixed. So nothing personal is committed, not even for a moment: no real names (the owner's included), email addresses, anything about a person who asked for a reading or what they asked, no tokens or cookies. The repository's own addresses (`bogheorghiu/i-ching`, and the release repository in `vasana-works`) are install paths, not personal data.

Example readings use invented questions. Model and API responses stay out of the repository unless they hold only public, academic content; cite a run by its request or generation ID instead.

If personal data does reach a commit, stop and tell the owner. Scrubbing history is their decision, not a side task.

**How it is enforced:** the PII gate, `AGENTS.md` section 5.
