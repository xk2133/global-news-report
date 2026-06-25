# Windows Execution Rules (CRITICAL)

These rules apply **only on Windows** (PowerShell / Git Bash / CMD). On Unix-like systems, standard `subprocess.run()` with `stdout=PIPE` typically works.

## Rule 1: spawnSync Only

Use `spawnSync`, **NOT** `execSync` — `execSync` misquotes JSON params on Windows.

```javascript
// ✅ CORRECT
const { spawnSync } = require('child_process');
const result = spawnSync('node', ['scripts/cli.mjs', 'call', server, tool, JSON.stringify(params)], {
  cwd: WIND_MCP_SKILL_DIR,
  encoding: 'utf-8'
});

// ❌ WRONG (breaks on Windows)
const { execSync } = require('child_process');
execSync(`node scripts/cli.mjs call ${server} ${tool} '${JSON.stringify(params)}'`);
```

## Rule 2: Bash Redirect for Python

Python `subprocess.run([node, cli.mjs, ...])` returns empty stdout on Windows.

**Workaround**: Redirect to temp file via Bash (`node cli.mjs ... > /tmp/out.json`), then parse with Python. Direct pipe also works.

```python
# ✅ CORRECT (Bash redirect)
import subprocess
cmd = f'cd "{WIND_MCP_SKILL_DIR}" && node scripts/cli.mjs call {server} {tool} \'{json.dumps(params)}\' > /tmp/out.json'
subprocess.run(['bash', '-c', cmd], check=True)
with open('/tmp/out.json', 'r') as f:
    data = json.load(f)

# ❌ WRONG (empty stdout on Windows)
result = subprocess.run(
    [node_exe, cli_mjs, 'call', server, tool, json.dumps(params)],
    capture_output=True, text=True, cwd=WIND_MCP_SKILL_DIR
)
# result.stdout may be empty on Windows
```

## Rule 3: Serial Fetches Only

Git Bash `&` + `>` redirect combos produce 0-byte files. **All Wind MCP calls must be serial** (one at a time, wait for completion).

```bash
# ✅ CORRECT (serial)
node cli.mjs call ... > /tmp/out1.json
node cli.mjs call ... > /tmp/out2.json

# ❌ WRONG (parallel, produces 0-byte files)
node cli.mjs call ... > /tmp/out1.json &
node cli.mjs call ... > /tmp/out2.json &
wait
```

## Rule 4: Temp Path Mismatch

Bash `/tmp/xxx.json` maps to `C:\Users\{user}\AppData\Local\Temp` on Windows (Git Bash). Python parse scripts must use the **Windows absolute path**.

```python
# ✅ CORRECT
tmp_dir = 'C:/Users/kongxy12/AppData/Local/Temp'
raw_path = f'{tmp_dir}/dji.json'

# ❌ WRONG (looks for /tmp on Windows, which may not exist)
raw_path = '/tmp/dji.json'
```

## Rule 5: `cd` Required for cli.mjs

`cli.mjs` references files via relative paths (e.g., `./references/`). Using absolute path to `cli.mjs` without `cd` → 0-byte output on Windows.

```bash
# ✅ CORRECT
cd "C:\Users\kongxy12\.claude\skills\wind-mcp-skill" && node scripts/cli.mjs call ...

# ❌ WRONG (cli.mjs can't find relative references)
node "C:\Users\kongxy12\.claude\skills\wind-mcp-skill\scripts\cli.mjs" call ...
```
