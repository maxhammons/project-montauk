# Equivalent mutants

A mutation score is only meaningful if the denominator is right. Some mutations
change the source without changing behaviour — no input can distinguish the
mutant from the original — so no test can ever kill them. Counting those as
failures makes 100% unreachable and turns the score into a number nobody can act
on.

Each entry below states the mutation, why it cannot be observed, and how
confident that claim is. **A mutation belongs in *Proven equivalent* only when
the argument is about behaviour, not about difficulty.** "I could not think of a
test" is not an equivalence proof. Entries under *Unreachable without a race*
are explicitly **not** claimed to be equivalent: they are observable in
principle, and what protects them is that no input — as opposed to no timing —
can reach them.

The machine-readable twin of this document is `tools/equivalent-mutants.txt`.
The sweep exits nonzero for any survivor not listed there, so a new survivor
cannot hide behind these, and every listed site must carry an argument here.

Re-check any of these with:

```sh
python3 tools/mutation_recheck.py <index> 1
```

## Proven equivalent

### `app.rs:439` — `vec![(root.to_path_buf(), false)]` → `true`

The boolean is `explicit_file` for the discovery root when no paths were given.

`explicit_file` is read in exactly two places. At `app.rs:413` it applies to
files, and the root is a directory. At `app.rs:398` it appears as
`!explicit_file && !relative.is_empty() && ignored(..)`, and for the root
`normalized_relative(root, root)` is `""`, so `!relative.is_empty()` is false
and the whole condition is false whatever `explicit_file` holds.

Directory entries are pushed with a literal `false` further down, so the value
never propagates. No input can reach a point where it is read.

### `toolchain.rs:124` — `.filter(|resolved| resolved != root)` → `==`

Decides whether to keep the canonicalised repository root for stripping
prefixes off tool-reported paths.

The two differ only when `canonicalize(root) != root`. When they are equal the
mutant stores `Some(root)`, and `relative()` tries `strip_prefix(resolved)`
first and `strip_prefix(&self.declared)` second — the same path, so the same
answer.

`root` cannot be non-canonical. It comes from `repository_root(&cwd())`, and
`cwd()` is `env::current_dir()`, which is `getcwd(3)` — defined to return a path
containing no symbolic links. Verified on this machine: a process launched with
its working directory set to a symlink still reports the resolved path.

```
$ mkdir -p symtest/real && ln -s real symtest/link
$ (cd symtest/link && python3 -c "import os; print(os.getcwd())")
/private/tmp/symtest/real
```

Ancestors of a canonical path are canonical, so `repository_root` cannot
introduce one either.

### `lint.rs:737` — `.unwrap_or(true)` → `false`

Supplies the mask value when `masked.get(token_start)` is `None`.

It sits behind `bytes[token_start..].starts_with(b"except") &&`. That can only
be true when `token_start < bytes.len()`, and `masked` is built by
`python_code_mask(bytes)` with exactly `bytes.len()` entries. So `get` always
returns `Some` and the default is unreachable.

### `lint.rs:740` — `!byte.is_ascii_alphanumeric() && *byte != b'_'` → `||`

Confirms `except` is a whole word rather than the head of a longer name.

The mutant is more permissive: it admits bytes that are alphanumeric or `_`.
For any such byte the code then computes
`after = skip_python_spacing(bytes, token_start + 6)`, and since that byte is
not whitespace, `after` stays put. The finding is then gated on
`bytes.get(after) == Some(&b':')` — but `:` is neither alphanumeric nor `_`, so
every byte the mutant newly admits fails that gate.

The two therefore agree on every input: the mutant admits strictly more bytes,
and every one of them is rejected one line later.

### `lint.rs:226` — `cursor = next + usize::from(next < bytes.len())` → `>=`

Steps past the newline of a heredoc terminator line.

`mark_range(mask, body_start, cursor)` has already run on the previous line with
the pre-update cursor, so the masked span is identical either way. What changes
is where scanning resumes: the original resumes after the terminator's newline,
the mutant on it.

A newline is inert in `quote_mask` — no branch matches it, so it falls to
`index += 1`. With a second heredoc the next body starts one byte earlier, which
adds that newline to the masked span. No rule reads the mask at a newline:
KENTO003 slices `[offset + start .. offset + content_end]` from within a line,
and `lines()` never includes the terminator. KENTO001 and KENTO002 do not
consult the mask at all.

When the terminator is the last line, `next == bytes.len()`: the original adds
0, the mutant adds 1, and `while cursor < bytes.len()` ends the loop on both.

## Unreachable without a race

Not claimed equivalent. Each of these is observable in principle, but reaching
the divergent branch requires the filesystem to change state *between two
adjacent calls in one run* — a timing condition, not an input. No test can
arrange that deterministically without fault injection Kento does not have, and
a test that arranges it probabilistically is a flake by construction. If fault
injection is ever added, these move out of this section.

### `app.rs:451` — `.unwrap_or(false)` → `true`

Supplies `explicit_file` for an argument path when `fs::symlink_metadata`
fails.

The value is only produced on the error branch, and `discover` opens with the
same `fs::symlink_metadata(&path)` call on that same path. That call fails
again and returns `Err("cannot inspect …")` before `explicit_file` is read.

Distinguishing the two takes a path that fails to stat in `lint_paths` and then
succeeds in `discover`, microseconds later.

### `toolchain.rs:103` — `return false` when a shell file cannot be read

Decides whether a file is zsh, and so whether ShellCheck is offered it. The
branch is the one where the file cannot be read at all.

`linted` holds only files `discover` already read successfully — reading them
is how their language was determined — so by the time this runs the file was
readable moments ago. Making the read fail here takes the file being removed or
locked between the two calls.

## Closed since this document was written

### `install.rs:367` — `!file_type.is_file() || file_type.is_symlink()` → `&&`

Guards hook state records against entries that are not regular files. This was
listed above as proven equivalent, and the argument was wrong.

For a **directory** the equivalence holds: the mutant reads it,
`read_to_string` fails, and the error maps to the identical
`"malformed hook state record"`. The argument then dismissed a **FIFO** because
reading one blocks forever "so it is not a usable input" — but blocking *is*
the divergence: the original refuses in milliseconds, the mutant hangs
indefinitely. An error versus a hang is observable behaviour, and a FIFO is one
`mkfifo` away from being an input.

`uninstall_refuses_a_fifo_hook_state_record_without_hanging` now kills it: it
plants a FIFO among the records and runs `uninstall` under a 10-second
deadline, so the original's refusal passes and the mutant's hang fails.

### `install.rs:484` — `error.kind() == ErrorKind::NotFound` → `!=`

Tolerates an already-absent hook while rolling back. It looked to need a race,
but the ordinary route reaches it: when the hook *write* fails there is no hook
to remove, so the rollback's `remove_file` returns `NotFound` on its own.
`install_refuses_a_hook_it_cannot_write` now asserts the refusal carries no
rollback complaint — a message that cries wolf about its own cleanup is one
nobody reads twice.

### `install.rs:709` — `error.kind() != ErrorKind::NotFound` → `==`

Filters the removal errors worth reporting during `undo_install`. Reaching it
through the CLI would take a filesystem that fails one removal mid-rollback, so
it is driven directly instead: `undo_install` is called from a unit test with a
`Staged` list naming a file that never existed, and then one naming a directory,
which cannot be removed as a file and whose error is not `NotFound`.

Both halves matter and they are opposite mistakes. Complaining about a file that
was already gone buries the real error under noise about a cleanup that
succeeded. Staying silent about a removal that genuinely failed leaves commands
behind that the next install refuses, with nothing in the message to say why.

## Scoring

Line numbers move when the file does; the entries above are current as of the
sweep artifact in `docs/`, and `tools/equivalent-mutants.txt` carries the same
sites in machine-readable form. Re-derive rather than trust: the sweep exits
nonzero if its survivors differ from that list in either direction's spirit —
any unlisted survivor fails it.

Seven mutations survive: five proven equivalent, two unreachable without a
race. Quoting the caught percentage without this document attached would be
dishonest: it is 100% *of what a test can reach within the operator set*, and
the operator set is eleven token swaps — statement deletion, return-value
replacement, and call-swap mutants were never in the population.
