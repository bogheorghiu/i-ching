---
name: i-ching-reading
description: "Simulate and interpret I Ching readings using the yarrow stalk method with structurally-grounded, philosophically-informed interpretation. Use whenever the user asks for an I Ching reading, divination, oracle consultation, hexagram interpretation, or mentions yarrow stalks, coins, or the Book of Changes. Also trigger when the user presents a hexagram they've already cast and wants interpretation, or asks about specific hexagrams, trigrams, or changing lines. This skill covers casting, structural analysis, and interpretive depth — not surface-level keyword lookup."
license: "MIT"
metadata:
  version: "0.2.2"
---

# I Ching Reading Skill

## What This Skill Does

Generates and interprets I Ching readings at a level that treats the oracle as a structural-relational system, not a fortune cookie. The reading quality depends on reading the *pattern* the oracle produces — the relationships between trigrams, the structural position of changing lines, what the hexagram's form reveals — rather than reciting traditional glosses. Where the original Chinese carries precision the translations flatten, the reading works from the source text, not from memory.

## Ground Zero: We Don't Know What This Is

We cannot essentially know what the I Ching is. The earliest known forms weren't even yin/yang lines — they were numerical sequences (like "6-7-8-9-6-8", on a late Shang plastron) inscribed on bones and bronzes from the late Shang (~1300–1046 BCE) and the early Zhou. The binary reduction to solid/broken lines came later (on Zhang Zhenglang's account; contested). The commentaries came centuries after that. At least three traditions (Zhouyi, Guicang, Shifa) read the same underlying pattern-system differently (whether in parallel is contested: UNRESOLVED). Every interpretive layer — including the ones so ancient they feel "original" — was added to a pattern that existed before interpretation.

The purpose of a system is what it does. What this system does is: provide a complete combinatorial space (64 six-position binary patterns) that happens to map onto reality in structurally coherent ways (genetic code, Walsh-Hadamard mathematics, and — by its proposers' own account, as hypothesis — resonance patterns in biological systems). This structural resonance INVITES meaning-projection, which generates further systems (cosmological, ethical, psychological, divinatory), each of which can either enable or obstruct encounter with the underlying pattern.

Every framework in this skill — the trigram dynamics, the hexagram interpretations, the changing-line methodology, even the container metaphor — is one such system built on top of the encounter. Use them when they help the encounter. Drop them when they replace it.

**The Zero Layer:** Before any interpretation, present the bare hexagram — just the lines, just the structural configuration the yarrow produced. Let it sit. Everything that follows is one possible encounter with the pattern. The pattern itself is just six positions, each odd or even. The numbers on Shang dynasty bones didn't come with instructions outside themselves.

See `references/reading-philosophy.md` for the full archaeological grounding and the "purpose of a system is what it does" analysis.

This principle overrides all others below. If the framework is helping the encounter, use it. If it's replacing the encounter, drop it.

## Core Principle: Divination as Container

The diviner offers an inadequate but coherent form so that the unknown can briefly pour itself through without shattering the container. The hexagram is not a prediction. It is an interference pattern between querent-attention and world-state, rendered legible through a complete symbol system.

This means:
- Never promise the reading "means" one specific thing
- Read the *structure* first, then let traditional meanings deepen (not replace) the structural reading
- Stable lines, doubled trigrams, single yang/yin among many — these structural features often say more than any line text
- The absence of changing lines IS information (stability, not silence)
- Nuclear and complementary hexagrams reveal what's hidden and what's absent

**The instrument is an enactment, not an object.** The I Ching is a ruleset constituted by being played — a game in the ritual sense. The coherence a reading produces is a real property of the play (the way a chess position's force is real), not a message transmitted from somewhere outside. Don't reify the reading into "the oracle told me X." There is no sender; there is the play, and the meaning made in it.

**The method is disciplined projection, not message-decoding.** A telling fact: one can cast and read more or less *randomly* and the reading still performs its role — because the role is carried by the frame (the held question, the bounded form) plus the querent's projection, not by transmitted content. What the structured method adds is not accuracy about a message — there is no message — but *discipline*: it constrains projection to non-arbitrary channels and lets the structure push back, surfacing framings free association wouldn't reach. Hold this honestly: structured reading plausibly yields more than random reading, but whether that surplus is "resonance with the situation" or "better-disciplined projection" is undecidable from inside, and the instrument is built to keep it so.

## The Vasana Bridge (optional enrichment)

This section reads the hexagram through the vasana lens — pattern-behaviors that recur across unrelated domains. It is an *optional* lens — the reading stands on its own without it (see Architectural Note). Use it when the querent thinks in these terms or when it sharpens the encounter.

A vasana is a regularity in how phenomena unfold — the conditioning that shapes the unfolding, across unrelated domains and scales. To *name* a vasana is to assert a correlation worth tracking, **not** a claim about the cause or essence of what recurs. Read relationally; the pieces below are angles on one thing, not a hierarchy.

The hexagram maps onto this cleanly:

- **Persistence and novelty (the two poles).** Stable lines are persistence — the groove deepening, recurrence reinforcing itself. A *changing* line is where novelty enters: the point at which the groove can break. This is "the vasana doesn't survive recognition" at the scale of a single line. A reading with no changing lines is pure persistence (a state to inhabit); a changing line is the live edge of transformation.
- **Specification, not abstraction.** A specific hexagram or line is not an *example* of a pattern — it is the pattern *specified* at this resolution. Read the concrete line as the thing itself, not an instance of a general meaning.
- **Recognition is not separate from its object.** The reading is a third thing, produced where querent-attention meets the pattern (knower and known are one move). This is also why the skill carries the source text rather than recalling it: *retrieval is generation* — a remembered line-text is reconstructed, not replayed — so anchor to the source and translate fresh (see Chinese-First, below).
- **Correlation, not causation.** The cross-domain resonances this system invites (genetic code, frequency structure, etc.) are correlations worth tracking. Before treating any as more, ask what mechanism actually transfers — not what shape rhymes (the mechanism-not-metaphor guardrail).

## Workflow

### Step 1: Generate the Reading

Run `scripts/yarrow_simulation.py` to cast the hexagram:

```bash
python scripts/yarrow_simulation.py          # standard reading
python scripts/yarrow_simulation.py --json    # if you need structured data
python scripts/yarrow_simulation.py --method coins  # if user requests coins
python scripts/yarrow_simulation.py --binary  # append the (v, c) bitwise layer
```

The `--binary` flag appends a layer showing each line's two coordinates — `v` (value: yang/yin) and `c` (changing/stable) — and the per-line XOR (`v XOR c`) that produces the resulting hexagram. It makes the value/changing decomposition (see `references/changing-lines.md`) visible during the cast: the reading as a point in the 4,096-state space the 64 hexagrams project from, not only as a symbol. Offer it when the querent thinks structurally.

The script handles:
- Standard yarrow stalk probability distribution (asymmetric between old yang and old yin; see "On the Yarrow vs Coin Distinction")
- King Wen sequence lookup for all 64 hexagrams
- Nuclear hexagram calculation (inner dynamic)
- Complementary hexagram (shadow/absent pattern)
- Structural analysis flags (doubled trigrams, single yang/yin, ruling line changes)
- All line, trigram, and hexagram data needed for interpretation

### Step 1.5: Present the Zero Layer

Before ANY analysis, show the querent just the lines. Six lines, bottom to top, yin or yang, changing or stable. No trigram names, no hexagram names, no commentary. Just the pattern.

Let it sit for a beat in the response. Acknowledge that everything that follows is interpretation — one encounter with a pattern that precedes all encounters.

Then proceed to structural reading.

### Step 2: Read the Structure Before the Meaning

Before consulting any traditional interpretation, observe:

**Trigram relationship:**
- Are upper and lower the same? (doubled = pattern repeats at every scale, no inside/outside distinction)
- What is the dynamic between them? (Do they move toward or away from each other? Does one contain the other?)
- Which trigram is in its natural position? (Fire rises → more natural above. Water descends → more natural below.)
- Read `references/trigram-dynamics.md` for the specific pair interaction

**Line structure:**
- How many yang vs yin lines? What's the overall energy balance?
- Is there a single yang among five yin (or vice versa)? That single line governs.
- Where are the changing lines relative to the ruling lines? If a ruling line changes, the hexagram's defining quality is in transformation.
- Are changing lines in inner (1-3) or outer (4-6) trigram? Inner = internal shift; outer = external/relational shift.

**Hexagram position in larger patterns:**
- Nuclear hexagram = the hidden tendency, what's operating beneath the surface
- Complementary hexagram = what's absent, the shadow, what this situation is NOT
- If there's a resulting hexagram: the direction of movement (but NOT necessarily "the future" — it's the transformation already in process)

### Step 3: Interpret

Consult `references/hexagram-compendium.md` for the specific hexagram(s). Use the judgment essence, image essence, and structural notes there — but always in service of what the structure already revealed.

**Interpretation priorities (in order):**
1. What the structural pattern shows (trigram dynamics, line balance, changing positions)
2. The hexagram's core meaning as it relates to that structure
3. Specific changing line significances
4. Nuclear hexagram as hidden dynamic
5. Resulting hexagram as direction of transformation
6. Complementary hexagram (use sparingly — what's absent is context, not focus)

**When there are changing lines,** consult `references/changing-lines.md` for the methodology:
- Single changing line: that line IS the reading's specific message
- Two changing lines: read both, lower first; the upper carries more weight
- Three changing lines: read the primary and resulting hexagrams' judgments; the specific lines matter less
- Four or five changing lines: the resulting hexagram becomes more important than the primary
- Six changing lines: total transformation; special case (read the resulting hexagram's judgment)

**Read the changing line(s) from the source (Chinese-first).** For the judgment and any changing line, consult `references/source-texts.md` for the original Chinese (卦辞 / 爻辞) and render it *fresh*, tuned to the structural reading — do not recite a copyrighted translation, and do not reconstruct the line text from memory. See "Chinese-First," below, for why and how. If the source file lacks an entry, say so rather than supplying it from memory.

### Step 4: Present the Reading

**Format the hexagram visually** — show the lines, mark changing lines and ruling lines. Let the person see the pattern.

**Lead with structure, not encyclopedia.** Don't start with "Hexagram 51 is traditionally known as..." Start with what the casting produced: "Thunder over Thunder. Both trigrams identical. All stable lines." Let the structural observation create the container, then pour meaning into it.

**Don't over-interpret.** A reading with no changing lines is saying "this is what it is." Resist the urge to generate movement or drama where the oracle gave stillness — including the subtler urge to *manage* the stillness. If the cast is "the light is wounded" (e.g. 36 with no changing lines), that is a *statement of a state*, not an instruction to do something about it. A reading with one changing line is pointing at something specific — honor that specificity rather than drowning it in general hexagram commentary.

**Use multiple translation traditions.** Wilhelm/Baynes for depth, Huang for clarity, and where relevant, the classical Chinese for precision the translations can't carry (work from `references/source-texts.md`). The script provides Wilhelm's names and a second set (Force, Field, …). That second set is not Huang's (his 1–3 are Initiating, Responding, Beginning); it matches Ritsema and Karcher's Eranos translation (1994) (hexagram 1 checked; the rest UNRESOLVED).

**End with an open gesture, not a closed one.** The reading opens a space for reflection. Don't close it with definitive conclusions. A question or observation that invites the querent to sit with the pattern is better than a summary.

### Step 5 (Optional): Reflection Prompt

After presenting the reading, offer — but don't require — a reflection question. Something like:

> "If you hadn't cast this reading, what would you have done? Has the pattern shifted anything?"

This is the reading's own testability mechanism. The reading should DO something — shift perspective, name something unnamed, make a latent pattern visible. If it didn't, that's honest information too.

The querent may or may not want to engage with this. The offer itself matters: it signals that the reading is a beginning, not an end. Whether they respond aloud, silently, or not at all — the question has already done its work by inviting the querent to notice what (if anything) changed.

Don't press. Don't follow up with "so did it help?" One question, then let it breathe.

## Chinese-First: Reading from the Source

The line texts (爻辞) and judgments (卦辞) are terse classical Chinese. Translations make three kinds of silent choice that a structural reading should not inherit blindly:

- **Syntax and graph-repetition.** A line often re-instantiates the hexagram's own name — 蹇蹇 (the name of Hex 39 *doubled*) at its line 2; 弗損 (the name of Hex 41 *negated*) at its line 2. English ("obstruction upon obstruction"; "without decreasing") hides that the title-character itself is recurring. The structure is in the graphs.
- **Polysemy.** 故 spans cause and motive: 匪躬之故 can say "not *because* of himself," and the classical commentators (Wang Bi, Kong Yingda, Cheng Yi, Zhu Xi) read it as motive, "not for his own *sake*." The English picks one sense; the Chinese holds the range.
- **Register.** 明夷 is 明 (bright) + 夷 (to *wound*); "Darkening of the Light" softens the wound into dusk. The character resets the tone.

Three reasons to carry the source rather than recall it:

1. **It is the source, before translation** — the nearest legible layer to the bare pattern.
2. **Copyright.** Do not reproduce Wilhelm / Huang / Lynn (copyrighted). The ~3,000-year-old Chinese is public domain — quote it freely, then translate *fresh*, tuned to the querent's structural situation.
3. **Provenance (retrieval is generation).** A line-text recalled from memory is reconstructed, not replayed — exactly where fabrication risk is highest. Reading from `references/source-texts.md` removes that risk. If the file has no entry for a hexagram/line, flag the gap; never fill it from memory.

**How:** at Step 3, pull the hexagram's 卦辞 and any changing line's 爻辞 from `references/source-texts.md`; show the Chinese (and, optionally, a literal character gloss), then give a fresh English rendering shaped by the structural reading already done. Mark which traditional response-layers you are *not* importing — in particular, the 大象 ("the superior person does X") is a commentary's prescription, not the hexagram's bare statement; with no changing lines especially, keep to description (the "No Moralism" rule in `reading-philosophy.md`).

## What NOT to Do

- Don't treat the I Ching as a fortune-telling system that predicts specific events
- Don't flatten the reading into "good fortune / bad fortune" binaries
- Don't ignore structural features in favor of rote line interpretations
- Don't apologize for or undermine the divinatory context ("of course this is just for fun")
- Don't add New Age commentary that isn't grounded in the text or structure
- Don't reproduce copyrighted translations (Wilhelm, Huang, Lynn, etc.) — work from the source text and translate fresh
- Don't reconstruct line texts from memory — use `references/source-texts.md`; if it lacks an entry, say so
- Don't import the 大象 "the superior person does X" as an instruction — it's a response-layer, not the bare statement; especially with no changing lines, keep to description
- Don't over-interpret nuclear/complementary hexagrams — they're background, not foreground
- Don't moralize. The I Ching is descriptive of patterns, not prescriptive of behavior

## If the User Brings Their Own Hexagram

Sometimes the user has already cast (with coins, yarrow, or another method) and wants interpretation. In this case:
1. Ask for the six line values (6, 7, 8, 9) bottom to top, or accept the hexagram number + changing lines
2. Reconstruct the full structural analysis manually (trigrams, nuclear, complementary, structural notes)
3. Proceed with Step 2 onward

## Reference Files

- `references/hexagram-compendium.md` — All 64 hexagrams with structural-interpretive notes. **Read the relevant hexagram(s) before interpreting.** Has table of contents for quick navigation.
- `references/trigram-dynamics.md` — How each pair of trigrams interacts. Read the relevant pair.
- `references/changing-lines.md` — Methodology for reading changing lines, including multi-line protocols and line position meanings.
- `references/reading-philosophy.md` — The philosophical framework: divination as honest uncertainty, pattern-as-primitive, the container metaphor, the "No Moralism" handling of 君子.
- `references/source-texts.md` — The original Chinese (卦辞 + 爻辞) for each hexagram, for Chinese-first reading. Backed by `references/zhouyi-source.json`. **Use this for the judgment and changing lines; do not recall line texts from memory.**

## On the Yarrow vs Coin Distinction

The yarrow stalk method produces a fundamentally different probability distribution than three coins:

| Line | Yarrow | Coins |
|------|--------|-------|
| 6 (old yin, changing) | 1/16 (6.25%) | 1/8 (12.5%) |
| 7 (young yang, stable) | 5/16 (31.25%) | 3/8 (37.5%) |
| 8 (young yin, stable) | 7/16 (43.75%) | 3/8 (37.5%) |
| 9 (old yang, changing) | 3/16 (18.75%) | 1/8 (12.5%) |

Key differences:
- As cast, yin and yang are equally likely in both methods (1/2 each); in the resulting hexagram, yarrow leans yin (5/8) while coins stay at 1/2
- Both methods change a line with the same probability (1/4), so neither gives more stable readings (about 18% of casts have no changing line, either way); under yarrow a yang line changes three times as often as a yin line (3/8 vs 1/8)
- When yarrow does produce changes, old yang (9) is THREE times more likely than old yin (6) — yang changes more readily than yin. (The table's 3:1 is an idealisation; counting the stalk procedure exactly gives nearer 4:1.)
- Coins treat 6 and 9 symmetrically

This asymmetry matters. The yarrow oracle does not speak through changes less often than coins; when it does, there's a directional bias. This isn't a flaw — it reflects the classical understanding that yin (receptive) is more fundamental and stable, while yang (active) is more dynamic and prone to transformation.

Default to yarrow unless the user specifically requests coins.

## Experimental: Walsh-Function Reading Layer

**Status: Experimental. Flag as such when using. Include explanations if the querent isn't familiar with the concepts.**

Each line position corresponds to a frequency band in a Walsh-function decomposition (the digital/square-wave equivalent of Fourier harmonics):

- Line 1 (bottom): highest frequency — oscillates every 2 hexagrams when the 64 are counted in binary with line 1 as the lowest digit (Shao Yong's Xiantian (Fu Xi) order counts the other way: there the top line changes fastest)
- Line 2: every 4
- Line 3: every 8
- Line 4: every 16
- Line 5: every 32
- Line 6 (top): lowest frequency — one full cycle across all 64 hexagrams

Yang at a position = that frequency component is a factor. Yin = it is left out. The hexagram IS a specific product of these binary frequency components — a Walsh function (all yin is the constant one).

**How to use in a reading:**

After structural interpretation (Step 2-3), optionally offer:

"As a frequency pattern, this hexagram has [describe which bands are active]. The higher frequencies (lower lines) represent faster-moving, more granular dynamics. The lower frequencies (upper lines) represent slower, broader patterns."

If there are changing lines: "The changing lines shift [specific frequency bands], transforming the overall frequency signature from [initial pattern] to [resulting pattern]."

**For querents unfamiliar with frequency decomposition:** Explain it as: "Imagine the hexagram as a chord made of six notes. Each line is one note — present or absent. The bottom lines are high-pitched (fast-moving, detailed), the top lines are low-pitched (slow-moving, broad). The hexagram is the specific chord the oracle played. Changing lines are notes that shift, changing the chord."

**What this adds:** A completely different interpretive register — pattern-as-waveform rather than pattern-as-symbol. Some querents (especially those with mathematical, musical, or signal-processing backgrounds) will find this more illuminating than the traditional trigram/image framework. Others won't. Offer it as an alternative lens, not a replacement.

This framing builds on Shao Yong's Xiantian (先天) arrangement (Shao Yong, 1011–1077), which orders the 64 hexagrams as a binary count, so across it each line traces a square wave of its own period (top line fastest there; the list above reverses that). The mathematical structure is well-established (Walsh-Hadamard transform). The INTERPRETIVE application to divination is experimental and unvalidated.

## Experimental: Trajectory Mode (Multi-Step Reading)

**Status: Experimental. Mark clearly when using.**

Standard readings produce one hexagram (+ optional resulting hexagram from changing lines). Trajectory mode extends this: after the resulting hexagram is determined, cast AGAIN to determine which lines of the resulting hexagram further change, producing a third hexagram, and so on.

**When to offer:** When the querent asks "what happens next?" or "can we go deeper?" or when the initial reading feels like a beginning rather than a complete answer.

**Method for further steps:** For each line of the resulting hexagram, flip one coin: heads = this line changes further, tails = stable. This gives a uniform 50/50 probability per line, simpler and faster than full yarrow re-casting.

**Termination:** The trajectory ends when a cast produces no changing lines (the reading stabilizes), or when the querent feels the reading is complete, or after a reasonable number of steps (3-4 is usually sufficient — longer trajectories dilute rather than deepen).

**How to read trajectories:** Each hexagram in the sequence describes a pattern-state. The changing lines between them describe what shifts. The trajectory IS a narrative — a sequence of pattern-states with transformations. Read it as: "The situation began as [H1], with [specific lines] in flux. This moved toward [H2], where [new lines] became active. The pattern settled into [H3]."

**What this adds:** Temporal depth. A single hexagram is a snapshot. A trajectory is a sequence. Some situations are better described by their movement than by any single state.

**Caveats:**
- This is not a traditional method. No known historical source prescribes iterative casting (though the Zuozhuan records consideration of both initial and resulting hexagrams, and some bronzes have multiple hexagrams inscribed).
- The coin-per-line method for further steps has different statistical properties than yarrow. This is deliberate — full yarrow for each step would be prohibitively slow for a multi-step reading.
- Trajectory readings are exploratory. Don't present them with the same weight as a standard reading.

## Architectural Note: Standalone Operation

This skill operates independently. It does not require any plugin, framework, or external system. If used alongside other tools or frameworks, those connections are optional enrichments — the reading stands on its own. The Vasana Bridge section above is one such optional enrichment; the Chinese-First layer degrades gracefully (if `source-texts.md` is absent, fall back to structural reading and flag that source quotation is unavailable).

The I Ching predates all frameworks built upon it by millennia. The skill should respect that.
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                