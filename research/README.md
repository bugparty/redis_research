# Research

Our own notes and analysis. Everything outside this folder is third-party
material pulled in as submodules; don't edit it. Write your findings here.

| Folder | Question it answers |
|---|---|
| [`version-comparison/`](version-comparison/README.md) | How did a given piece of code, and the annotators' explanation of it, change between 2.6, 2.8.2, 3.0, 5.0.5 and 7.0.5? |
| [`architecture/`](architecture/README.md) | How is Redis put together: its subsystems, how they interact, and why it was designed that way? |
| [`commands.md`](commands.md) | What do the common commands do, and where is each one implemented? |

## Conventions

- **One topic per Markdown file**, in kebab-case: `dict-rehash.md`, `event-loop.md`.
  When a topic grows, turn it into a folder with its own `README.md`.
- **Cite code by tree, path and line**, e.g. [`redis-3.0-annotated/src/dict.c:212`](https://github.com/huangz1990/redis-3.0-annotated/blob/8e60a75884e75503fb8be1a322406f21fb455f67/src/dict.c#L212).
  Write the plain reference in backticks, then run `scripts/permalink.py` to turn
  it into a GitHub permalink at the pinned submodule commit. In a note that
  cites one tree a lot, declare its base once with
  `<!-- code-base: redis7.0-chinese-annotated/src -->` and write just `` server.c:6836 `` (the double backticks here keep this example from being converted).
  For a release that isn't the pinned commit, add the ref after `@`:
  `<!-- code-base: redis/src @ 7.4.2 -->`. Links then point at that tag's
  commit, which `permalink.py` fetches if the shallow submodule lacks it.
  Mermaid and other code blocks are left alone, since links don't render there.
  Run `scripts/permalink.py --check` before committing.
  Line numbers depend on the pinned submodule commit, so a bump of the
  submodule pointer can make them stale.
- **Quote, don't paraphrase, when comparing comments.** Keep the original
  Chinese and add an English translation under it.
- **Separate fact from interpretation.** Mark your own guesses or
  conclusions so they don't read like documented behavior.
- **Diagrams:** prefer Mermaid in a fenced block (` ```mermaid `) so they
  render on GitHub and stay diffable. Put images in an `img/` folder next to
  the note.
