hydra-sandbox — hardened Python sandbox for LLM-generated code

1/ I built a Python sandbox that actually blocks attacks. Not just a
timeout — import guards, seccomp syscall filtering, landlock FS sandbox,
and 20+ escape vectors tested.

Open source. Zero deps. pip install hydra-sandbox.
github.com/akaradje/hydra-sandbox

2/ The problem: every LLM agent runs model-generated code. Most tools
use exec() or bare subprocess. If the model hallucinates
`os.system('dangerous')` — that runs on your HOST.

hydra-sandbox runs it in a hardened child process instead.

3/ Import guard blocks dangerous modules at the find_spec level:
• import subprocess → PermissionError
• __import__('ctypes') → blocked
• compile('import shutil','','exec') + exec() → blocked
• hex-encoded payloads → blocked

4/ Multiple strategies, auto-detected:
• subprocess: cross-platform, Python-level isolation
• seccomp: Linux syscall filtering (kills fork/exec/socket)
• landlock: Linux FS sandbox (can't read /etc/passwd)
• seccomp+landlock: strongest available

5/ Z3 formal verification. Prove your code is correct BEFORE executing:

spec = {"args": {"x": "Int", "y": "Int"},
        "postcondition": "result == x + y"}
result = verified_execute(code, "add", spec)

6/ Escape test suite — 20 bypass attempts tested:
✅ __import__('subprocess')
✅ importlib.import_module('subprocess')
✅ compile+exec chains
✅ hex-encoded imports
✅ sys.modules poisoning
⚠️ os.system (known limitation, requires seccomp)

7/ Merkle audit trail — every execution produces a tamper-evident log
entry chained via SHA-256. verify_chain() detects tampering.
export_csv() for compliance.

8/ Works with LangChain, LlamaIndex, CrewAI. Drop-in replacement for
the default PythonREPL tool. Examples in ./examples/

89 tests, 0 failures. Python 3.10+ on Linux/macOS/Windows.
Try it: pip install hydra-sandbox
