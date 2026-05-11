After spending a week trying to safely execute LLM-generated Python in a production agent, I extracted and published **hydra-pysandbox** — a pure-Python package with 3-layer isolation, Z3 formal verification, and Merkle audit trails.

**Why not just use subprocess.run()?** It leaks env vars, allows network calls, has no memory limits, and won't stop a fork bomb.

**What hydra-pysandbox does:**
- 3 isolation layers (subprocess + import guard + rlimits)
- Blocks 20 known escape techniques (tested)
- Optional Z3 SMT verification for generated functions
- Merkle audit trail for compliance
- Cross-platform (Linux/Mac/Windows)
- Zero required deps for core

**Install:**

    pip install hydra-pysandbox

**Quick demo:**

```python
from hydra_sandbox import execute_python

# Blocked imports caught
r = execute_python("import subprocess", timeout=5)
print(r.blocked_imports)  # ['subprocess']

# Safe code runs fine
r = execute_python("print(sum(range(100)))", timeout=5)
print(r.stdout)  # 4950
```

GitHub: https://github.com/akaradje/hydra-sandbox

Happy to answer questions!