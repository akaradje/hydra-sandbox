"""
Example: LangChain agent using SafePythonTool.

Demonstrates a ReAct agent with safe Python execution.

Requirements: pip install hydra-pysandbox[langchain] langchain-openai
"""

from hydra_sandbox.integrations.langchain import SafePythonTool

# Create the safe tool (drop-in for PythonREPL)
tool = SafePythonTool(
    timeout=10,
    allow_network=False,
    strategy="auto",
)

# ---- Integration sketch (requires langchain-openai) ----
# from langchain_openai import ChatOpenAI
# from langgraph.prebuilt import create_react_agent
#
# llm = ChatOpenAI(model="gpt-4o")
# agent = create_react_agent(llm, [tool])
# agent.invoke({"messages": [{"role": "user", "content": "Calculate 2+2 using Python"}]})


if __name__ == "__main__":
    # Test the tool directly (no LLM needed)
    print("Testing SafePythonTool directly:")
    print("=" * 40)

    result = tool._run("print(sum(range(100)))")
    print(f"Safe code: {result}")

    result = tool._run("import subprocess")
    print(f"Blocked import: {result}")

    print("=" * 40)
    print("Tool ready for LangChain agents. Uncomment the sketch above to use.")
