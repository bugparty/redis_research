# Research

Our own notes and analysis. Everything outside this folder is third-party
material pulled in as submodules; don't edit it. Write your findings here.

| Folder | Question it answers |
|---|---|
| [`version-comparison/`](version-comparison/README.md) | How did a given piece of code, and the annotators' explanation of it, change between 2.6, 2.8.2, 3.0, 5.0.5 and 7.0.5? |
| [`architecture/`](architecture/README.md) | How is Redis put together: its subsystems, how they interact, and why it was designed that way? |

## Conventions

- **One topic per Markdown file**, in kebab-case: `dict-rehash.md`, `event-loop.md`.
  When a topic grows, turn it into a folder with its own `README.md`.
- **Cite code by tree, path and line**, e.g. `redis-3.0-annotated/src/dict.c:212`.
  Line numbers depend on the pinned submodule commit, so a bump of the
  submodule pointer can make them stale.
- **Quote, don't paraphrase, when comparing comments.** Keep the original
  Chinese and add an English translation under it.
- **Separate fact from interpretation.** Mark your own guesses or
  conclusions so they don't read like documented behavior.
- **Diagrams:** prefer Mermaid in a fenced block (` ```mermaid `) so they
  render on GitHub and stay diffable. Put images in an `img/` folder next to
  the note.
