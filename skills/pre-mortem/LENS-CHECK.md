# Lens Check — Coverage Without a Cage

Klein's pre-mortem uses *open* failure generation; the lenses below exist to force
coverage after the freeform dump, not to constrain what gets raised. Run the lens
check in step 5 of `PREMORTEM-LOOP.md`, after the merged list exists.

## The three lenses

Each lens attacks a different upstream doc and hunts a different decay. This is why
the pre-mortem reads all three docs — each answers a failure question the others can't.

| Lens | "We failed because…" | Traces to | Violations it hunts |
|------|----------------------|-----------|---------------------|
| **Outcome / ROI** | shipped, but the business goal/metric never moved | requirements (goal) | Paper Tiger |
| **Operational** | shipped & worked at launch, then broke — incidents, bugs, scaling, data loss | tech-design | Black Box, Silent Fallback, Computational Friction |
| **Delivery** | never shipped / late / blocked / scope exploded | issues/tickets | Distributed Monolith |

For each lens, ask: *did the merged list raise at least one mode here?* If a lens is
empty, that emptiness is itself a finding — either the plan is genuinely de-risked on
that axis (state why) or the draft missed it (generate now). Record coverage in
frontmatter `lenses_covered`.

## The mundane-mode rule

The classic pre-mortem trap is over-producing dramatic modes (competitor attack,
market shift, novel tech failure) and missing the dull killers that sink most
projects. **At least two mundane modes must be present before `status: complete`.**

Mundane modes to probe explicitly if absent:
- Key person quits / goes on leave / gets pulled to a higher priority.
- A dependency (team, vendor, upstream service, library) slips its date.
- Scope creep — "just one more thing" repeated until the date is gone.
- No clear owner for some slice; it falls between two people.
- Onboarding/handoff cost — the one person who understands X is unavailable.

If the merged list has fewer than two of these, prompt for them by name. Record
`mundane_mode_count` in frontmatter.

## Why coverage is a checklist, not a gate on generation

Running the lens check *before* the freeform dump would anchor the user to these
categories and defeat the independence the protocol depends on (see
`PREMORTEM-LOOP.md`). Coverage is verified *after* generation, never before.
