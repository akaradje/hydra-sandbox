## First public release 🎉

Production-grade Python sandbox for untrusted and LLM-generated code.

### Install

    pip install hydra-pysandbox

### Features
- **3-layer isolation**: subprocess boundary + import guard + resource limits
- **Z3 formal verification** (optional extra)
- **Merkle audit trail** — tamper-evident compliance logs
- **20 escape attack vectors tested** — ~85% blocked at subprocess level
- **Cross-platform**: Linux, macOS, Windows
- **Zero required dependencies** for core package

### Quick start

```python
from hydra_sandbox import execute_python

result = execute_python("print(42)", timeout=5)
print(result.stdout)  # "42"
```

### Links
- 📦 PyPI: https://pypi.org/project/hydra-pysandbox/
- 🔒 Security: security@hydra-sandbox.xyz

### Acknowledgements

Extracted from [Hydra RSI Core](https://github.com/akaradje/HYDRA_AGI_TECHNICAL),
an experimental multi-agent AGI research framework.
