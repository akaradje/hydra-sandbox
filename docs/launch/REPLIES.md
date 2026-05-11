# Launch Day Reply Templates

Pre-written responses for common questions. Paste and adapt as needed.

## "How does this compare to e2b.dev?"

Good question. e2b is a great cloud service — they run code in their own
VMs. hydra-pysandbox is the opposite: it's a pure Python library that runs
in YOUR process, no cloud, no account.

Trade-offs:
- e2b: better isolation (full VM), their service, ~500ms startup
- hydra-pysandbox: ~30ms startup, self-hosted, no per-execution cost,
  weaker isolation than a VM

They're complementary — you might use hydra-pysandbox for fast local agent
loops and e2b for production multi-tenant workloads.

## "Why not just Docker?"

Docker is great but heavy — 100ms+ startup, daemon required, not bundled
with Python. For an agent that wants to execute a 10-line snippet, Docker
is overkill.

hydra-pysandbox targets the "I need to safely exec this RIGHT NOW" case.
If you need multi-tenant or serious adversarial isolation, stack Docker/
gVisor/Firecracker on top.

## "Is this actually secure?"

Depends on your threat model. It's:
- Strong enough for: preventing LLM hallucinations from causing damage
  (most common case), EdTech, CTF platforms, code review bots
- NOT strong enough for: multi-tenant SaaS running adversarial attacker
  code

For adversarial workloads, stack hydra-pysandbox inside a Firecracker
microVM or gVisor. The README has a threat model table.

## "Why Z3? That's overkill."

It's optional! Core install doesn't include Z3.

But when it IS useful: financial calculations, medical dosages, crypto
contracts, compliance-critical code. LLMs hallucinate; Z3 can prove
behavior matches spec.

Example: "prove this add() never returns negative for non-negative
inputs." Z3 solves in milliseconds.

## "Can you break out of this sandbox?"

Probably, if you try hard enough in the `subprocess` strategy. That's
why there are 3 strategies:

- `subprocess` — good for most LLM output
- `seccomp` (Linux) — kernel-enforced syscall filter
- `seccomp+landlock` (Linux 5.13+) — kernel FS sandboxing too

Please file an issue if you find an escape! Escape tests in
`tests/test_escape_attempts.py` are the most valuable contributions.

## Generic praise / "I'll check it out"

Thanks! Would love to hear how it works in your use case. If you find
any escape technique that isn't in the test suite, please file an issue
— those are the highest-value contributions.

## "Can I use [framework X]?"

Yes! It's just a function call. Works with LangChain, LlamaIndex, DSPy,
or custom agents. There's an example in `examples/llm_repl_tool.py`.

## "What about performance?"

~30ms cold start per exec in subprocess strategy. AST pre-flight
validation is <1ms. If you need lower latency, check the benchmarks
in `docs/benchmarks.md` — we compare against naive `subprocess.run()`.

## "How does this relate to Hydra RSI Core?"

Hydra RSI Core is an experimental AGI research framework I've been
building (multi-agent code synthesis, SAE features, causal memory).
hydra-pysandbox is the sandbox module extracted and polished for
standalone use. The research project is separate and much more
experimental.

## For negative/hostile comments

Respond once, calmly, with facts. If they keep attacking:
- Thank them for the feedback
- Point to the threat model doc
- Stop engaging

Example:
"Thanks for the feedback. The threat model in SECURITY.md is explicit
about what we do and don't protect against. Happy to hear specific
suggestions for improvement."
