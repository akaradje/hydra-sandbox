"""
Example: Safely running student-submitted code for automatic grading.

Extracts the expected function signature and runs a battery of test
cases in the sandbox, returning a grade and feedback.

Requirements: pip install hydra-pysandbox
"""

from hydra_sandbox import execute_python, extract_expected_signature, verify_ast_signature


def grade_submission(
    code: str,
    function_name: str,
    test_cases: list[tuple[tuple, object]],
    timeout: int = 5,
) -> dict:
    """Run student code against test cases in the sandbox.

    Args:
        code: Student-submitted Python code.
        function_name: Name of the function to test.
        test_cases: List of (args_tuple, expected_output) pairs.
        timeout: Maximum execution time in seconds.

    Returns:
        Dict with grade, feedback, and per-case results.
    """
    # 1. Extract the expected signature from the code itself
    sig = extract_expected_signature(f"function '{function_name}'")
    if sig:
        _, expected_args = sig
        ast_error = verify_ast_signature(code, function_name, expected_args)
        if ast_error:
            return {"grade": 0, "feedback": f"Signature error: {ast_error}", "cases": []}

    # 2. Wrap code with test harness
    harness = f"{code}\n\n"
    harness += "import json\n"
    harness += f"results = []\n"
    for i, (args, expected) in enumerate(test_cases):
        args_str = ", ".join(repr(a) for a in args)
        harness += f"try:\n"
        harness += f"    actual = {function_name}({args_str})\n"
        harness += f"    results.append({{'case': {i}, 'passed': actual == {repr(expected)}, 'actual': actual}})\n"
        harness += f"except Exception as e:\n"
        harness += f"    results.append({{'case': {i}, 'passed': False, 'error': str(e)}})\n"
    harness += "print(json.dumps(results))\n"

    # 3. Execute in sandbox
    result = execute_python(harness, timeout=timeout, strategy="auto")
    if not result.success or result.timed_out:
        return {"grade": 0, "feedback": f"Execution failed: {result.stderr}", "cases": []}

    # 4. Parse results
    import json

    try:
        cases = json.loads(result.stdout.strip().split("\n")[-1])
    except (json.JSONDecodeError, IndexError):
        return {"grade": 0, "feedback": "Could not parse output.", "cases": []}

    passed = sum(1 for c in cases if c.get("passed"))
    grade = round(passed / len(cases) * 100) if cases else 0
    return {"grade": grade, "feedback": f"{passed}/{len(cases)} tests passed.", "cases": cases}


if __name__ == "__main__":
    # Grade a student's 'add' function
    code = "def add(x, y):\n    return x + y"
    tests = [((1, 2), 3), ((0, 0), 0), ((-1, 1), 0)]
    report = grade_submission(code, "add", tests)
    print(f"Grade: {report['grade']}%")
    print(report["feedback"])
