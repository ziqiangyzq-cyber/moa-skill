# Publish Codex MoA Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the tested cancellation and Responses-integrity fixes in a GitHub source layout that can reproduce an isolated Codex MoA installation.

**Architecture:** Keep shared runtime-neutral code at the repository root and add a `runtimes/codex/` overlay. An allowlist installer copies shared files and overlay-managed Codex files without touching private runtime state.

**Tech Stack:** Bash, Python 3 standard library, `unittest`, local loopback HTTP servers, GitHub Draft PR.

## Global Constraints

- Start from the current `origin/main` on `agent/publish-moa-integrity-fixes`.
- Never commit `roster.yaml`, root `adapters/*.sh`, `runs/`, environment files, endpoints, or credentials.
- Do not call external models or use real API credentials.
- Preserve the Claude-oriented root `SKILL.md` and its support for `agent:` adapters.
- Use strict RED -> GREEN for each production behavior.
- Push normally and open a Draft PR; never force-push `main`.

---

### Task 1: Publish Reliable Process-Group Supervision

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_moa_call.py`
- Modify: `bin/moa-call:21-47`

**Interfaces:**
- Consumes: an executable adapter path, prompt bytes on stdin, and positive finite `MOA_TIMEOUT` seconds.
- Produces: normalized non-empty stdout; exit `124` on timeout, `130` on `SIGINT`, `143` on `SIGTERM`, `5` on empty output, or the adapter failure status.

- [ ] **Step 1: Write shared wrapper regressions**

Create `tests/test_moa_call.py` with three real shell-adapter cases:

```python
def test_success_returns_adapter_output(self):
    adapter = self.make_adapter("cat >/dev/null\nprintf WRAPPER_OK\n")
    result = subprocess.run(
        [str(MOA_CALL), str(adapter)], input="prompt", text=True,
        capture_output=True, env={**os.environ, "MOA_TIMEOUT": "5"},
        check=False,
    )
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(result.stdout.strip(), "WRAPPER_OK")

def test_timeout_allows_exit_trap_to_remove_prompt_file(self):
    leak = self.root / "prompt.txt"
    adapter = self.make_adapter(
        "trap 'rm -f \"$LEAK_FILE\"' EXIT TERM INT\n"
        "cat > \"$LEAK_FILE\"\nsleep 5\n"
    )
    result = subprocess.run(
        [str(MOA_CALL), str(adapter)], input="confidential prompt", text=True,
        capture_output=True,
        env={**os.environ, "MOA_TIMEOUT": "0.3", "LEAK_FILE": str(leak)},
        timeout=3, check=False,
    )
    self.assertEqual(result.returncode, 124, result.stdout + result.stderr)
    self.assertFalse(leak.exists())

def test_sigterm_stops_adapter_process_group(self):
    heartbeat = self.root / "heartbeat.txt"
    pid_file = self.root / "adapter.pid"
    adapter = self.make_adapter(
        'printf "%s" "$$" > "$ADAPTER_PID_FILE"\n'
        'while :; do printf x >> "$HEARTBEAT_FILE"; sleep 0.05; done\n'
    )
    process = subprocess.Popen(
        [str(MOA_CALL), str(adapter)], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={**os.environ, "MOA_TIMEOUT": "30",
             "HEARTBEAT_FILE": str(heartbeat),
             "ADAPTER_PID_FILE": str(pid_file)},
        start_new_session=True,
    )
    adapter_pid = None
    try:
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if pid_file.exists() and heartbeat.exists() and heartbeat.stat().st_size >= 2:
                adapter_pid = int(pid_file.read_text())
                break
            time.sleep(0.05)
        self.assertIsNotNone(adapter_pid, "adapter did not start")
        os.kill(process.pid, signal.SIGTERM)
        self.assertEqual(process.wait(timeout=3), 143)
        stopped_size = heartbeat.stat().st_size
        time.sleep(0.3)
        self.assertEqual(heartbeat.stat().st_size, stopped_size)
        with self.assertRaises(ProcessLookupError):
            os.killpg(adapter_pid, 0)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=2)
        if adapter_pid is not None:
            try:
                os.killpg(adapter_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()
```

Use `tempfile.TemporaryDirectory`, `start_new_session=True`, a three-second
condition deadline, and close both captured pipes in `finally`.

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 -W error::ResourceWarning -m unittest \
  tests.test_moa_call.MoaCallTests.test_sigterm_stops_adapter_process_group -v
```

Expected: FAIL with the old visible shell returning `-15`, while test cleanup
terminates the adapter process group.

- [ ] **Step 3: Replace the layered timeout wrapper**

Keep the header and executable check. Require `python3`, then `exec python3 -c`
as the visible supervisor. The Python block must:

```python
process = subprocess.Popen(
    [adapter], stdin=sys.stdin.buffer, stdout=subprocess.PIPE,
    stderr=sys.stderr.buffer, start_new_session=True,
)

def group_exists():
    process.poll()
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return process.poll() is None
    return True

def handle_signal(signum, _frame):
    stop_group(signum)
    raise SystemExit(128 + signum)
```

`stop_group` sends the initial signal to `process.pid` as a PGID, allows one
second, sends `SIGKILL` only if the group remains, and reaps the direct child.
Use `process.communicate(timeout=timeout_s)` so partial output is never printed
on timeout or cancellation.

- [ ] **Step 4: Verify GREEN and commit**

Run:

```bash
python3 -W error::ResourceWarning -m unittest tests.test_moa_call -v
bash -n bin/moa-call
```

Commit the two files with a Lore-formatted message and exact tested commands.

---

### Task 2: Publish The Codex Responses Overlay

**Files:**
- Create: `runtimes/codex/adapters/codex.py`
- Create: `runtimes/codex/adapters/codex.sh`
- Create: `tests/test_codex_adapter.py`

**Interfaces:**
- Consumes: prompt text on stdin plus active Codex provider configuration and its environment-key credential.
- Produces: output text only for a decoded Responses object whose top-level `status` is exactly `completed`.

- [ ] **Step 1: Write the local-loopback Responses tests**

Create a fake `ThreadingHTTPServer` handler with a class-level response payload.
The success payload includes `status: completed`. A subclass returns:

```python
response_payload = {
    "status": "incomplete",
    "incomplete_details": {"reason": "max_output_tokens"},
    "output": [{
        "type": "message",
        "content": [{"type": "output_text", "text": "PARTIAL_RESULT"}],
    }],
}
```

The incomplete test requires non-zero status, exactly empty stdout, and both
`incomplete` and `max_output_tokens` on stderr. The success test also asserts
that the request contains no `tools`, and has `store` and `stream` set to false.
Start the incomplete test with
`self.assertTrue(ADAPTER.exists(), "Codex Responses adapter is not published")`
so the initial missing-file state is an assertion failure rather than a process
launch error.

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 -m unittest \
  tests.test_codex_adapter.CodexResponsesAdapterTests.test_rejects_incomplete_response_with_partial_text -v
```

Expected: FAIL with `Codex Responses adapter is not published`.

- [ ] **Step 3: Add the tool-free adapter and strict status gate**

Publish the credential-free adapter used by the installed Codex runtime. After
JSON decoding and API error-object handling, gate before any output extraction:

```python
status = payload.get("status")
if status != "completed":
    details = payload.get("incomplete_details")
    reason = details.get("reason") if isinstance(details, dict) else None
    suffix = f" ({reason})" if reason else ""
    die(f"Responses API returned non-completed status {status!r}{suffix}", 5)
```

The launcher resolves its own directory and `exec`s `codex.py`. Both files must
be executable and contain no fixed endpoint, model name, or credential value.

- [ ] **Step 4: Verify GREEN and commit**

Run:

```bash
python3 -m unittest tests.test_codex_adapter -v
bash -n runtimes/codex/adapters/codex.sh
python3 -m py_compile runtimes/codex/adapters/codex.py
```

Commit the overlay adapter and its tests with a Lore-formatted message.

---

### Task 3: Compose A Reinstallable Codex Skill

**Files:**
- Create: `runtimes/codex/README.md`
- Create: `runtimes/codex/SKILL.md`
- Create: `runtimes/codex/agents/openai.yaml`
- Create: `runtimes/codex/bin/moa-preflight`
- Create: `runtimes/codex/roster.example.yaml`
- Create: `runtimes/codex/scripts/bootstrap-local.sh`
- Create: `scripts/install-codex.sh`
- Create: `tests/test_codex_install.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: a source checkout and optional destination path.
- Produces: a composed Codex skill while preserving destination-private state.

- [ ] **Step 1: Write installer preservation tests**

In a temporary destination, create sentinel `roster.yaml`,
`runs/sentinel.txt`, and `adapters/custom.sh`. Run `scripts/install-codex.sh`
with that destination and assert all sentinel bytes remain unchanged. Also
assert these managed files exist and are executable where appropriate:

```text
SKILL.md
agents/openai.yaml
adapters/codex.py
adapters/codex.sh
bin/moa-call
bin/moa-preflight
prompts/proposer.md
roster.example.yaml
scripts/bootstrap-local.sh
```

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 -m unittest tests.test_codex_install -v
```

Expected: FAIL because `scripts/install-codex.sh` does not exist.

- [ ] **Step 3: Add the allowlist installer and overlay metadata**

The installer accepts `destination="${1:-${CODEX_HOME:-$HOME/.codex}/skills/moa}"`.
Implement `copy_shared` and `copy_overlay` helpers that create parent directories
and call `cp` only for explicit file paths. Copy shared prompts/examples as
explicit directory trees; never copy `.git`, `runs`, `roster.yaml`, env files,
or root private adapters. Apply the overlay last and restore executable bits.

Publish the already-validated Codex `SKILL.md`, strict file-backed preflight,
UI metadata, two-vendor example roster, and deterministic bootstrap. Update the
root README with separate Claude and Codex setup commands and the isolation rule.

- [ ] **Step 4: Verify GREEN and commit**

Run:

```bash
python3 -m unittest tests.test_codex_install -v
bash -n scripts/install-codex.sh runtimes/codex/scripts/bootstrap-local.sh
```

Commit the installer, overlay metadata, test, and README with a Lore-formatted
message.

---

### Task 4: Integrated Verification And Draft PR

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run the complete deterministic suite**

```bash
python3 -W error::ResourceWarning -m unittest discover -s tests -v
bash -n bin/moa-call scripts/*.sh runtimes/codex/adapters/*.sh \
  runtimes/codex/scripts/*.sh
python3 -m py_compile runtimes/codex/adapters/codex.py tests/*.py
```

- [ ] **Step 2: Validate a freshly composed installation**

Install into a temporary directory, run the official skill validator when
available, create a deterministic two-worker fake roster, and run the composed
`bin/moa-preflight`. Confirm no heartbeat worker remains.

- [ ] **Step 3: Audit the publication diff**

Run `git diff --check`, inspect `git status --short`, list every tracked file,
and scan the diff for credential patterns, endpoint values, `roster.yaml`, and
`runs/`. Review the full branch diff against `origin/main`.

- [ ] **Step 4: Request code review and address findings**

Review the exact branch diff against this plan. Fix every Critical or Important
finding and rerun the complete suite.

- [ ] **Step 5: Publish**

Push `agent/publish-moa-integrity-fixes` with tracking and create a Draft PR into
`main`. The PR body must describe the two root causes, runtime isolation,
installer preservation contract, deterministic checks, and the fact that no
real model call or credential was used.
