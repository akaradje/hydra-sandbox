"""
CLI entry point for hydra-pysandbox.

Usage::

    hydra-pysandbox run script.py --timeout 10 --strategy seccomp
    hydra-pysandbox check script.py --expect-function compute --expect-args x y
    hydra-pysandbox bench
    hydra-pysandbox doctor
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="hydra-pysandbox",
        description="Hardened Python execution sandbox CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ---- run ----
    run_parser = sub.add_parser("run", help="Execute a Python file in the sandbox")
    run_parser.add_argument("file", type=Path, help="Python file to execute")
    run_parser.add_argument("--timeout", type=int, default=5, help="Timeout in seconds")
    run_parser.add_argument("--strategy", default="auto",
                            choices=["auto", "subprocess", "seccomp", "landlock", "seccomp+landlock"],
                            help="Sandbox strategy")
    run_parser.add_argument("--allow-network", action="store_true", help="Allow network access")

    # ---- check ----
    check_parser = sub.add_parser("check", help="AST signature check on a file")
    check_parser.add_argument("file", type=Path, help="Python file to check")
    check_parser.add_argument("--expect-function", required=True, help="Expected function name")
    check_parser.add_argument("--expect-args", nargs="*", default=[], help="Expected parameter names")

    # ---- bench ----
    sub.add_parser("bench", help="Run benchmarks")

    # ---- doctor ----
    sub.add_parser("doctor", help="Report available strategies and isolation level")

    # ---- verify-annotation ----
    va_parser = sub.add_parser("verify-annotation", help="Verify a proof annotation in a Python file")
    va_parser.add_argument("file", type=Path, help="Python file with proof annotation to verify")

    args = parser.parse_args(argv)

    if args.command == "run":
        _cmd_run(args)
    elif args.command == "check":
        _cmd_check(args)
    elif args.command == "bench":
        _cmd_bench()
    elif args.command == "doctor":
        _cmd_doctor()
    elif args.command == "verify-annotation":
        _cmd_verify_annotation(args)


def _cmd_run(args) -> None:
    from hydra_sandbox import execute_python

    code = args.file.read_text(encoding="utf-8")
    result = execute_python(
        code,
        timeout=args.timeout,
        strategy=args.strategy,
        allow_network=args.allow_network,
    )
    print(f"Success: {result.success}")
    print(f"Exit code: {result.exit_code}")
    print(f"Timed out: {result.timed_out}")
    if result.stdout.strip():
        print(f"stdout:\n{result.stdout}")
    if result.stderr.strip():
        print(f"stderr:\n{result.stderr}")
    if result.blocked_imports:
        print(f"Blocked imports: {result.blocked_imports}")


def _cmd_check(args) -> None:
    from hydra_sandbox import verify_ast_signature

    code = args.file.read_text(encoding="utf-8")
    error = verify_ast_signature(code, args.expect_function, args.expect_args)
    if error is None:
        print(f"OK: '{args.expect_function}' matches expected signature.")
    else:
        print(f"FAIL: {error}")
        sys.exit(1)


def _cmd_bench() -> None:
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/benchmarks", "--benchmark-only", "-v"],
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    sys.exit(result.returncode)


def _cmd_doctor() -> None:
    import platform

    from hydra_sandbox.strategies import available_strategies

    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}")
    print(f"Available strategies: {', '.join(available_strategies())}")

    # Probe each strategy
    from hydra_sandbox.strategies import get_strategy

    for name in ("subprocess", "seccomp", "landlock", "seccomp+landlock"):
        try:
            strat = get_strategy(name)
            print(f"  {name}: READY")
        except Exception as exc:
            print(f"  {name}: UNAVAILABLE ({exc})")

    # Quick smoke test
    print()
    try:
        from hydra_sandbox import execute_python

        result = execute_python("print('doctor smoke test OK')", timeout=5)
        if result.success:
            print("Smoke test: PASSED")
        else:
            print(f"Smoke test: FAILED ({result.stderr})")
    except Exception as exc:
        print(f"Smoke test: ERROR ({exc})")


def _cmd_verify_annotation(args) -> None:
    from hydra_sandbox.proof import parse_proof_annotation, verify_proof_annotation

    code = args.file.read_text(encoding="utf-8")
    parsed = parse_proof_annotation(code)
    if parsed is None:
        print("No proof annotation found in the file.")
        sys.exit(1)

    print(f"Function:     {parsed.function_name}")
    print(f"Precondition: {parsed.precondition}")
    print(f"Postcondition:{parsed.postcondition}")
    print(f"Z3 result:    {parsed.z3_result}")
    print(f"Proof hash:   {parsed.proof_hash}")
    print(f"Verified at:  {parsed.verified_at}")
    print()

    if verify_proof_annotation(code):
        print("Result: VALID — proof annotation is intact.")
    else:
        print("Result: TAMPERED — proof hash does not match.")
        sys.exit(1)


if __name__ == "__main__":
    main()
