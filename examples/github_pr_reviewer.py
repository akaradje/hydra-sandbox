"""
Example: GitHub PR review bot that safely executes suggested code.

Sketch of a bot that comments on PRs, extracts Python code blocks from
the diff, runs them in the sandbox, and reports results.

Requirements: pip install hydra-sandbox
"""

import hashlib
import re

from hydra_sandbox import execute_python


def extract_code_blocks(diff_text: str) -> list[tuple[int, str]]:
    """Extract Python code blocks from a unified diff."""
    blocks: list[tuple[int, str]] = []
    current_block: list[str] = []
    current_start: int = 0
    in_block = False

    for lineno, line in enumerate(diff_text.split("\n"), start=1):
        if line.startswith("+"):
            if not in_block:
                current_start = lineno
                in_block = True
            current_block.append(line[1:].rstrip())
        else:
            if in_block and current_block:
                blocks.append((current_start, "\n".join(current_block)))
                current_block = []
                in_block = False

    if in_block and current_block:
        blocks.append((current_start, "\n".join(current_block)))

    return blocks


def review_diff(diff_text: str) -> list[dict]:
    """Run every added code block in the sandbox and return results."""
    results = []
    for line, code in extract_code_blocks(diff_text):
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:12]
        result = execute_python(code, timeout=10, strategy="auto")
        results.append({
            "line": line,
            "code_hash": code_hash,
            "success": result.success,
            "output": result.stdout[:200] or result.stderr[:200],
        })
    return results


if __name__ == "__main__":
    sample_diff = """
+def add(a, b):
+    return a + b
+
+print(add(2, 3))
"""
    for r in review_diff(sample_diff):
        status = "PASS" if r["success"] else "FAIL"
        print(f"Line {r['line']} [{r['code_hash']}]: {status} — {r['output']}")
