import os
import warnings
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_community.tools import DuckDuckGoSearchRun  # Simple web tool (optional)
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader  # For files
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OllamaEmbeddings
from langchain.tools.retriever import create_retriever_tool
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

# Suppress Pydantic warning
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")

# Load env (optional)
load_dotenv()

# Step 1: Set up Ollama model
model = ChatOllama(model="llama3.1:8b", temperature=0)  # Your model


# Step 2: File Access - Index local docs (e.g., PDFs in ./docs folder)
def setup_file_retriever():
    if not os.path.exists("docs"):
        os.makedirs("docs")
        print("Created ./docs folder—add your files (PDFs, TXT, etc.) there!")
        return None

    loader = DirectoryLoader("docs", glob="**/*.pdf", loader_cls=PyPDFLoader)
    docs = loader.load()

    embeddings = OllamaEmbeddings(model="llama3.1:8b")
    vectorstore = FAISS.from_documents(docs, embeddings)
    vectorstore.save_local("faiss_index")

    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    return retriever


file_retriever = setup_file_retriever()
file_tool = None
if file_retriever:
    file_tool = create_retriever_tool(
        file_retriever,
        "file_search",
        "Searches and returns relevant excerpts from your local documents. Use for file-based queries.",
    )


# Step 3: Define Custom Tools
@tool
def math_solver(expression: str) -> str:
    """Solves math expressions. Input: a valid Python math expression."""
    try:
        result = eval(expression)  # Safe for math; extend with sympy
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"


# Web search (optional; comment out for offline)
# search = DuckDuckGoSearchRun()

tools = [math_solver]
if file_tool:
    tools.append(file_tool)
# tools.append(Tool.from_function(function=search, name="web_search", description="Searches the web."))  # If using

# Step 4: Agent Setup (Updated for LangGraph)
prompt = PromptTemplate.from_template(
    """
You are a helpful local AI assistant. Use tools to access files or compute. Respond concisely.

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Question: {input}
{agent_scratchpad}
"""
)

# For LangGraph, use the prompt as a system message for state_modifier
system_msg = SystemMessage(content=prompt.partial(tools=str(tools), tool_names=[t.name for t in tools]).format())
agent = create_react_agent(model, tools, state_modifier=system_msg)

# Note: LangGraph agents are invoked directly (no AgentExecutor needed)
# We'll handle verbose logging manually in the loop for simplicity

# Step 5: Interactive Chat Loop
if __name__ == "__main__":
    print("Local Agent Ready! Type 'exit' to quit.")
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == "exit":
            break

        # Invoke the LangGraph agent (input as messages)
        input_msg = HumanMessage(content=user_input)
        response = agent.invoke({"messages": [input_msg]})

        # Extract output (last message is usually the final answer)
        output = response["messages"][-1].content
        print(f"Agent: {output}")
