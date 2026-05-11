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
