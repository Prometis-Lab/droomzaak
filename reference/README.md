# reference/ — inspiration materials (local-only, gitignored)

A scratch area for **inspiration** while building Droomzaak. Everything here **except this README is gitignored** — it stays on your machine and never enters the repo (these are other people's repos and/or large local material, not ours to commit).

Drop in anything that helps you build faster from the PRD:
- **Public repos** worth learning from — map applications, MapLibre / deck.gl examples, FastAPI + LLM-agent / tool-loop patterns, open-data / geo pipelines, etc. (`git clone` them here).
- **A prior implementation** of your own, if you have one, to mine for patterns.
- Design references, screenshots, API docs, dataset samples.

The `reference-scout` agent mines whatever is here for ideas, then you build the actual feature from the **PRD + data-shortlist** — the spec is the PRD, never a copy of any reference. If `reference/` is empty, the scout just works from the PRD + the architecture summary in `CLAUDE.md`; nothing breaks.

Suggested layout (any subfolder name is fine):
```
reference/<repo-or-project-name>/    # a cloned repo or your prior project
reference/notes.md                   # what you took from where
```

(The inherited `prometis_toolkit` geocoder lives separately in `inherited/`, also gitignored.)
