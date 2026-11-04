# Harness methodology: what the research taught, and how to build on it

**Status:** design proposal, 2026-11-04. The owner may change any part of it.

**Tags.**
- **GROUNDED** cites a file. "F" means `docs/harness/INPUT-findings.md`, followed by its section name.
- **UNRESOLVED** means not verified in this repository.
- **Gap** means a needed piece that does not exist yet.

**Claims about Claude Desktop and MCP.** No file in this repository documents Claude Desktop or MCP behaviour. Every claim below about them is therefore UNRESOLVED until it is checked against current documentation or a one-call test.

## 1. The pattern in one paragraph

Six habits made the work reliable:

- **One owner for keys and routing.** A single module decides which key and which endpoint every call uses.
- **Caps on real spend.** Every call is capped on the money actually spent, not on the field that reads zero.
- **Robust transport.** Long calls are streamed, and truncated answers are continued and stitched.
- **Resumable jobs.** Every job can pick up from files, because processes die.
- **Scripts do the work.** Models are called only where judging language is unavoidable, and code checks every model output.
- **Corroboration and records.** Load-bearing artefacts are checked by an independent model. Questions are pre-registered. Every call is recorded with its generation id in a ledger that another session can read.

Agents earn their keep by writing and patching the script, not by running open-ended loops. Almost all of this is independent of the research topic, so it translates to a general harness. The topic-specific parts are listed in section 4.

## 2. Layers

### 2.1 Routing and keys

**What it does.** It reads keys from the environment only, chooses the endpoint and provider, and fails loudly when a key is missing.

**Rules learned**
- One module reads keys; everything else calls it. Where a cloud proxy injects credentials, placeholder keys work. (GROUNDED: F, Routing; `research/keys.py` docstring)
- Claude can run through OpenRouter on the owner's own Anthropic key (BYOK) by pinning `provider.only=['anthropic']`. The generation record then shows `is_byok=true`, cost 0, and the real spend in `upstream_inference_cost`. (GROUNDED: F, Routing)
- An OpenRouter workspace weekly budget counts BYOK spend. Hitting it stops every call mid-run, so check limits as well as credits. (GROUNDED: F, Routing; `WRITE-PIPELINE.md` addendum)
- Cloud network rules match literal path prefixes, trailing slash included. A session's environment description can lag the settings, so test each rule with one call. (GROUNDED: F, Routing)
- The owner's OpenRouter guardrail redacts phone, email and IP-like strings, which can hit ISBNs. Keep raw page content out of guarded calls. (GROUNDED: F, Routing; `WRITE-PIPELINE.md` 1e)

**What exists.** `research/keys.py` provides OpenRouter chat, generation lookup and DeepSeek search. `docs/cloud-environment.md` lists the secrets and allowed hosts.

**Gaps**
- `keys.py` has no DeepSeek fetch and no DeepSeek Anthropic-style `/anthropic/v1/messages` endpoint, although the pipeline uses both.
- There is no preflight that checks the budget, limits and each network rule with one call. Which OpenRouter endpoint reports limits is UNRESOLVED.
- There is no per-call flag for "zero data retention required" or "guarded, so send no raw pages".
- The TypeScript agent reads `OPENROUTER_API_KEY` and `DEEPSEEK_API_KEY` itself (`agent.ts`, `tools/index.ts`), which breaks the one-module rule.

### 2.2 Cost and caps

**What it does.** It counts real spend per call and per job, stops cleanly at a cap, and keeps token use efficient.

**Rules learned**
- Under BYOK, cost fields read 0, so cost-based stop conditions never fire. Cap on `upstream_inference_cost`, plus `cost` for non-BYOK calls. (GROUNDED: F, Cost; `WRITE-PIPELINE.md` req. 3)
- Without prompt caching, an agent loop resends its whole context at every step (input grew from 1k to 52k tokens over 16 steps).
  - Anthropic automatic caching needs a top-level `cache_control` in chat completions, or `cacheControl` in `@openrouter/agent`. The snake_case form is silently dropped there.
  - In a probe, the second call cached 4,011 tokens and its cost fell from 0.0101 to 0.00045.
  - (GROUNDED: F, Cost)
- Maximum reasoning effort can consume all of `max_tokens`. Opus returned an empty answer after 32k tokens of reasoning; DeepSeek produced 64k thinking tokens and no text, ignoring its budget. Set `reasoning.max_tokens` explicitly, and set `max_tokens` near the model's real output limit rather than a habit number. (GROUNDED: F, Cost)

**What exists**
- `WRITE-PIPELINE.md` specifies the upstream-cost cap, `--max-usd`, and a `calls.jsonl` log with model, generation id, tokens and cost.
- `agent.ts` sets `cacheControl`.

**Gaps**
- `agent.ts` stops on the SDK's `maxCost(8)`. Whether that reads the BYOK-zero field is UNRESOLVED. If it does, the cap never fires.
- There is no shared budget accountant across processes or sessions.
- There is no model table of real output limits, reasoning parameters, caching style and prices. DeepSeek's own API needs a price table, otherwise cost is logged as tokens only.

### 2.3 Transport

**What it does.** It gets a complete, parseable answer back.

**Rules learned**
- Long non-streamed calls drop. DeepSeek reset connections, OpenRouter sent padding before the JSON, and Kimi raised IncompleteRead. Stream long calls and strip padding before parsing. (GROUNDED: F, Transport)
- Opus 5.5 rejects assistant prefill. Continue a truncated answer with a new user turn, then stitch the parts. (GROUNDED: F, Transport)
- Retry each call twice on connection errors. (GROUNDED: `WRITE-PIPELINE.md` req. 5)

**What exists.** `keys.py` strips the blank and `:`-prefixed padding lines and uses a 600-second timeout.

**Gaps**
- `keys.py` does not stream.
- It catches only `HTTPError`, so resets and IncompleteRead crash the caller.
- It has no retry and no continue-and-stitch helper.

### 2.4 Resumable jobs

**What it does.** Every unit of work is saved as soon as it finishes, and a rerun skips what is done.

**Rules learned**
- Cloud worker restarts killed background processes several times in one day. Every long job must resume from files. (GROUNDED: F, Transport)
- Save progress after every item, and save every raw response. (GROUNDED: `WRITE-PIPELINE.md` req. 1, 5)

**What exists.** The pipeline specification requires stages that resume from files, `snapshots/`, and `calls.jsonl`.

**Gaps**
- There is no reusable job store; each script reimplements resumability.
- A call that was in flight when the process died is lost. Whether OpenRouter's generation lookup returns the completion text, or only metadata, is UNRESOLVED.

### 2.5 Scripted pipelines, with models only where language judgment is needed

**What it does.** Code does harvesting, fetching, comparison and bookkeeping. A model is called for a bounded judgment, such as extracting fields, writing a clue or flagging an item, and code then checks the output.

**Rules learned**
- Open agent loops failed on this task. Sonnet and Opus, each at maximum reasoning with the same prompt, collected about 200 source snapshots and closed 0 items in about 37 calls each. (GROUNDED: F, Agents vs scripts)
- The scripted pipeline accepts or drops each candidate in one pass. Its fourth test produced the first verified item. (GROUNDED: F, Agents vs scripts)
- The agent's best use is writing and patching the script. Opus wrote 1,531 lines. Three function-level patches, based on evidence from runs, cost about $0.4–0.7 each and were applied by an AST-based applier. (GROUNDED: F, Agents vs scripts; `research/battery2/pipeline/apply_patch.py`)
- Code checks model output. For example, every extracted field must appear verbatim in its snapshot or the field is dropped, and leakage and identifiability are checked in code. (GROUNDED: `WRITE-PIPELINE.md` 1c, 1f)
- An agent with a shell tool installed a package unasked. Forbid installs explicitly. (GROUNDED: F, Agents vs scripts)

**What exists**
- `WRITE-PIPELINE.md` is a reusable specification pattern.
- `apply_patch.py` applies function-level patches.
- `tools/index.ts` confines file access to a work directory.

**Gaps**
- The shell tool passes `env: process.env`, so the agent sees every API key.
- The install ban lives only in the prompt; nothing enforces it.
- The work-directory check uses `startsWith`, so a sibling such as `/work2` passes a `/work` check.
- `apply_patch.py` neither re-parses nor tests its result, and crashes if `main()` is missing.

### 2.6 Verification and corroboration

**What it does.** It makes results trustworthy before anyone relies on them.

**Rules learned**
- Pre-register before any run. Check keys against the fact's own record before the run: one key copied from a secondary note was wrong. Record deviations, with reasons, before the data they affect. A bar may be raised after results, never lowered. (GROUNDED: F, Verification; `research/battery2/PREREG.md`)
- A model's memory gives leads, never evidence. Models agreeing from memory confirms nothing, because their errors are correlated. (GROUNDED: `docs/research-method.md`)
- Corroborate load-bearing artefacts with an independent, cheap, strong model. DeepSeek Flash independently wrote the same pipeline, 1,747 lines. (GROUNDED: F, Verification)
- Run blind design rounds: eight models proposed, seven critiqued, one merged. List disagreements rather than averaging them. (GROUNDED: F, Verification; `PREREG.md`)
- Verify blind: shuffle items and strip writer labels. Drop flagged items; never repair them. (GROUNDED: `WRITE-PIPELINE.md` 1g and addendum)
- Five well-cited calibration items cannot separate a model that is selective but accurate from one that is lucky. Abstention varied from 0 to 80% across models. (GROUNDED: F, Verification)

**What exists.** `PREREG.md`, `research-method.md`, and the pipeline checks.

**Gaps**
- There is no generic `corroborate` routine that sends an artefact to N models blind and reports their disagreements.
- There is no tool for comparing two independently written artefacts.
- Calibration set sizes are too small to be informative.

### 2.7 Coordination and records

**What it does.** It lets sessions, scheduled tasks and the owner share what is running, what the environment really does, and what each claim rests on.

**Rules learned**
- A shared board carries in-flight heavy calls and dated environment facts between sessions. (GROUNDED: F, Coordination)
- Record every generation id, so the owner can pull the logs. Keep a ledger per lead with quote, URL, date, tool, id and tier. (GROUNDED: `research-method.md` steps 2 and 5)

**What exists.** `calls.jsonl`, and the ledger specification in `research-method.md`.

**Gaps**
- The board, called the "Delegation artifact", lives outside the repository; where exactly is UNRESOLVED.
- There is no ledger schema or tool.
- Environment facts are dated but never re-tested automatically.

## 3. Packaging options

### (i) Standalone harness library and CLI

**What it gives.** All seven layers as tested code: a call wrapper, a model table, a job store, a budget accountant, corroboration and a ledger. Scripts, cloud sessions and agents can all use it, and it can be developed and tested in this repository's existing cloud environment (GROUNDED: `docs/cloud-environment.md`).

**What it cannot do.** It cannot be used from a Claude Desktop conversation without a wrapper.

**Cost.** Only the model spend it caps.

**Risks**
- Keys stay in environment variables, as today.
- Prompt injection from third-party outputs is limited, because outputs land in files and pass code checks before any model reads them.

### (ii) An MCP server for Claude Desktop and Claude Code

**What it gives.** Claude in a chat could call tools such as:
- `delegate(model, prompt, caps)`
- `corroborate(artefact, models)`
- `ledger()`
- job status

This would use other models, and the Claude API on the owner's key via BYOK routing (GROUNDED: F, Routing), from inside a conversation.

**What is UNRESOLVED about the platform.** Claude Desktop and Claude Code can load MCP servers. All of the following must be checked before design depends on them:
- how a local server is configured;
- how secrets are passed to it;
- tool-call timeouts;
- whether progress or long-running tools are supported;
- whether results can be returned as files rather than text.

**What it cannot do**
- It cannot run long calls synchronously if tool calls time out. The safe design, whatever the platform turns out to support, is `delegate` returning a job id at once, plus a `status` tool, backed by the job store from (i).
- A local server runs only while the machine is awake. That this applies to a Desktop-launched server is an inference, so UNRESOLVED.

**Cost**
- Claude Desktop tokens spent reading results back. Keep results short; return summaries and file paths.
- The delegated model spend.

**Risks**
- **Keys.** Keys would live on the owner's computer. Where and how is UNRESOLVED, but never in the repository or a chat (GROUNDED: `keys.py` error message).
- **Prompt injection.** Third-party model output returned into Claude's context can carry instructions. Mitigations:
  - mark outputs as untrusted data;
  - cap their size;
  - expose no shell or file-write tool in the server;
  - never let the server act on content inside an output.
- **Guardrails.** The owner's OpenRouter guardrail still applies, so the redaction rule holds (GROUNDED: F, Routing).
- **Spend.** One chat could launch costly jobs. Per-call and per-day caps must sit in the server, not in the prompt.

### (iii) A cloud scheduled task as a courier

This is the other session's approach (GROUNDED: F, Coordination).

**What it gives.** Calls run with no laptop open, using environment secrets, and results are written to Drive.

**What it cannot do**
- It cannot answer interactively; latency depends on the schedule. Schedule limits are UNRESOLVED.
- It is still subject to worker restarts and network-rule quirks (GROUNDED: F, Routing and Transport).
- It needs Drive access. How the courier reaches Drive is UNRESOLVED.

**Cost.** Model spend, plus whatever the scheduled environment costs (UNRESOLVED).

**Risks**
- Secrets in a cloud environment.
- Results in Drive readable by anything with Drive access.
- The same injection risk when results are read back.
- Duplicated code if the courier does not share the library.

### Recommendation

Build **(i) first, then (ii) as a thin wrapper over it**, and later move the courier (iii) onto the same library and job store.

**Reason.** Every rule learned lives in code: the cap on upstream cost, streaming and stitching, resumability, code-checked outputs and the ledger. None of it lives in the transport. Options (ii) and (iii) each need that same core, and without it they would reimplement it badly. Option (i) can also be built and tested now, here, while the Desktop facts are being verified.

### Build order, smallest first

1. **Harden the core call.** Grow `keys.py` into a `harness` package:
   - streaming;
   - catching resets and IncompleteRead;
   - two retries;
   - padding strip;
   - continue-and-stitch;
   - a `calls.jsonl` entry for every call, with generation id and upstream cost.
2. **Model table.** Real output limits, the reasoning parameter, caching syntax and prices. Calls set `max_tokens` and `reasoning.max_tokens` from it.
3. **Budget and preflight.** A spend cap across processes, plus a one-call check of credits, limits and each network rule, logging dated environment facts.
4. **Job store.** File-backed jobs with ids, resume, and status.
5. **CLI.** `harness call`, `harness job submit|status`, `harness ledger`.
6. **Corroborate.** N models, blind, shuffled; disagreements listed, never averaged.
7. **Agent hygiene.**
   - Route the TypeScript agent's keys through the harness configuration.
   - Strip keys from the shell environment.
   - Enforce the install ban and fix the path check.
   - Make `apply_patch.py` re-parse its result and run a smoke test.
8. **MCP server.** `delegate`, `status`, `corroborate` and `ledger` over the CLI, with no shell tool and outputs marked untrusted. Start this only after the UNRESOLVED platform facts above are checked.
9. **Courier.** Rebuild it to submit and drain the same job store.

## 4. What does not translate

**Topic-specific rules.** These belong to Chinese bibliography and stay in the research pipeline:
- the ctext.org exclusion;
- CNKI, VIP and Wanfang counting as one custodian class;
- two library catalogues from different institutions counting as independent (GROUNDED: `PREREG.md`, Deviations);
- traditional-to-simplified comparison;
- the three-character leakage rule;
- DeepSeek search's strength on Chinese databases (GROUNDED: `research-method.md`).

**Battery 2 decisions.** The admission thresholds, the owner adjudicating up to 20 items, and production reasoning settings for models under test (GROUNDED: `PREREG.md`).

**The agent-versus-script numbers.** The figures (about 37 calls, 0 items) come from one session on one search-and-verify task. They support "script it" for bounded, checkable work. They do not show that agents fail at everything.

**Version-bound details.** Model names, output limits, prices, and the OpenRouter padding format will drift. They belong in the model table, dated, not in code logic.

**Account-specific settings.** The guardrail's settings and the workspace budget belong to the owner's account. The harness should read and respect them, not assume them.

**DeepSeek's tool API.** It offers no zero-retention guarantee, so it suits public, academic queries only (GROUNDED: `keys.py`). General use needs a policy per data class.

## 5. Open questions for the owner

1. **Desktop use.** Is Claude Desktop mainly for asking quick second opinions in a chat, or for launching long jobs? The answer decides whether `delegate` must be asynchronous from day one.
2. **Keys on the desktop.** Where should keys live on the desktop machine, and may the MCP server hold an OpenRouter key with a separate, lower workspace budget?
3. **Repository.** Should the harness live in this repository until it is stable, or start in its own repository, perhaps the `semi-autonomous` template, as `cloud-environment.md` suggests?
4. **Language.** Python only, with the TypeScript agent calling it, or both?
5. **The board.** Should the Delegation board move into the repository as a file the harness writes?
6. **The courier.** Should it be rebuilt on the library, or retired once the MCP server exists?
7. **Default caps.** What should the defaults be, per call, per job, per day, and against the weekly workspace limit?
8. **Corroboration panel.** Which models make up the default panel, and must it always include one non-Anthropic model?
9. **Untrusted output.** Should third-party output ever reach Claude's context directly, or only as a file path plus a short code-checked summary?
10. **Retention.** Which kinds of call require zero data retention, and should the harness refuse them when no ZDR endpoint exists?

<!-- drafted by anthropic/claude-opus-5.5 via OpenRouter BYOK, generation gen-1793787559-VixegdQW5iITXPSKHMOI -->
