"""
Example: LlamaIndex agent using safe Python execution.

Demonstrates FunctionTool created by hydra-pysandbox.

Requirements: pip install hydra-pysandbox[llamaindex]
"""

from hydra_sandbox.integrations.llamaindex import create_safe_python_tool

# Create the safe tool
tool = create_safe_python_tool(
    timeout=10,
    allow_network=False,
    strategy="auto",
)

# ---- Integration sketch (requires llama-index and an LLM) ----
# from llama_index.llms.openai import OpenAI
# from llama_index.core.agent import ReActAgent
#
# llm = OpenAI(model="gpt-4o")
# agent = ReActAgent.from_tools([tool], llm=llm)
# agent.chat("Calculate 2 + 2 using Python")


if __name__ == "__main__":
    # Test the tool directly
    print("Testing LlamaIndex tool directly:")
    print("=" * 40)

    result = tool("print(42 * 2)")
    print(f"Safe code: {result}")

    result = tool("import ctypes")
    print(f"Blocked import: {result}")

    print("=" * 40)
    print("Tool ready for LlamaIndex agents.")
