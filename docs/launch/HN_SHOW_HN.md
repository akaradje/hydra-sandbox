Show HN: hydra-sandbox — hardened Python sandbox for LLM-generated code

I built an open-source Python sandbox that lets you safely execute
untrusted code. It's designed for LLM agents, code review bots, and
anyone who needs to run model-generated or user-submitted Python without
risking their host system.

What makes it different from a naive subprocess:

• Import guard — blocks dangerous stdlib modules (subprocess, ctypes,
  socket, multiprocessing) at the Python import hook level. Catches
  __import__, importlib, compile+exec, and hex-encoded bypass attempts.

• Multiple isolation strategies — cross-platform subprocess (default),
  Linux seccomp-bpf (syscall filtering), and landlock (filesystem
  sandbox). Auto-detection picks the strongest available.

• Z3 formal verification — optional pre/post-condition checking. Prove
  add(x,y) returns x+y mathematically before executing it.

• Merkle audit trail — tamper-evident JSONL execution log. Every entry
  chains to the previous via SHA-256.

• Escape attempt suite — 20+ known bypass vectors tested, including
  MRO walks, sys.modules poisoning, and compiled code execution.

Zero required dependencies. Python 3.10+ on Linux/macOS/Windows.

GitHub: https://github.com/akaradje/hydra-sandbox
Docs: https://akaradje.github.io/hydra-sandbox

I'd love feedback from anyone running untrusted code in production.
What am I missing? What would make you trust a sandbox for your use case?
