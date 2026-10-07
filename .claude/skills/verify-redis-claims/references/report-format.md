# Report format

Write the report in the language the user is using. Keep it scannable: the
reader wants to know what to fix, how sure you are, and where to look.

```markdown
## <note path> 核查（基于 <tree>@<short sha>，版本 <x.y.z>）

结论：N 处错误，M 处不精确，K 处过期链接。<one sentence on the most important one>

### 问题

1. **<file>:<line>，<severity>**
   - 原文：<quote the claim, short>
   - 实际：<what is true, with the condition that makes the original false>
   - 证据：<source path:line> / `<command>` → `<output>`
   - 建议：<one-line fix, optional>

### 核对无误
- <grouped list of what was checked and held up, with the method: 源码 / gdb / strace / 实测>

### 未能核实
- <anything you couldn't check and why>
```

## Severity

- **wrong** — the statement is false for the version the note describes, or its
  stated reason is false even if the conclusion holds.
- **imprecise** — true only under conditions the note doesn't state, an
  absolute ("always", "only", "never", "every") with counterexamples, a count
  or number that's off, or a citation a few lines off.
- **stale-link** — a permalink that doesn't resolve, points at a non-pinned
  commit, or whose line no longer holds the cited code.
- **omission** (optional) — the note isn't wrong but leaves out something a
  reader would need (an extra limit, a new option).

Rank wrong first. Don't inflate: a minor wording slip is imprecise, not wrong.
When a later version behaves differently from the version described, mention it
as context, not as an error.

## Evidence

Paste the smallest thing that proves the point: one source line with its
path:line, one command with its output, a 3–5 line excerpt of a trace. Name the
setup when it matters (`--appendfsync always`, RESP2, `--maxclients 1`).
