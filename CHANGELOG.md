# Changelog

All notable changes to hydra-pysandbox will be documented in this file.

## [0.1.0] — 2026-05-11

### Added
- `execute_python()` with subprocess, seccomp, and landlock strategies
- Import guard blocking dangerous stdlib modules
- AST signature verification (`verify_ast_signature`, `extract_expected_signature`)
- Z3 formal specification checker (`check_spec`, `VerificationSpec`, `VerificationResult`)
- `verified_execute()` combining sandbox execution with Z3 proofs
- Merkle audit trail (`AuditLog`)
- CLI entry point (`hydra-pysandbox`)
- Escape attempt test suite

## [0.2.0] — 2026-05-11

### Added
- Proof-Carrying Code: cryptographic `ProofAnnotation` with SHA-256 hash,
  embeddable comment blocks, and `verify_proof_annotation()` for auditing
- LangChain integration: `SafePythonTool` (`hydra-pysandbox[langchain]`)
- LlamaIndex integration: `create_safe_python_tool()` (`hydra-pysandbox[llamaindex]`)
- PEP 561 `py.typed` marker for IDE autocomplete
- Type stubs and deprecation warning decorator
- CLI command: `hydra-sandbox verify-annotation <file.py>`
- `benchmarks/bench_execute.py` with real cold-start numbers
- Documentation: integration guides, proof-carrying-code, updated benchmarks

### Fixed
- `exit_code=-9` (SIGKILL equivalent) on timeout instead of `None`
- Consistent import guard error messages across platforms
- `__version__` re-exported in strategy registry module for debugging

### Dependencies
- New optional: `hydra-pysandbox[langchain]` (`langchain-core>=0.3`)
- New optional: `hydra-pysandbox[llamaindex]` (`llama-index-core>=0.11`)

[0.2.0]: https://github.com/akaradje/hydra-sandbox/releases/tag/v0.2.0
[0.1.0]: https://github.com/akaradje/hydra-sandbox/releases/tag/v0.1.0
