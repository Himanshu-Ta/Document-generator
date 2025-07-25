# docstring_generator.py

import os
import ast
from pathlib import Path
from typing import Dict, Any, List, Optional, TypedDict

from dotenv import load_dotenv
import google.generativeai as genai
from langgraph.graph import StateGraph, END

# --- Environment Setup ---
load_dotenv()
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")


# --- State Schema ---
class DocstringItem(TypedDict, total=False):
    name: str
    lineno: int
    col_offset: int
    code_block: str
    docstring: Optional[str]


class State(TypedDict, total=False):
    file_path: str
    output_path: str
    source_code: str
    missing: List[DocstringItem]
    docstrings: List[DocstringItem]
    updated_code: str
    status: str
    error: str


# --- LangGraph Nodes ---
def read_file_node(state: Dict[str, Any]) -> Dict[str, Any]:
    file_path = state["file_path"]
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()
    return {**state, "source_code": code}


def parse_missing_docstrings_node(state: Dict[str, Any]) -> Dict[str, Any]:
    source_code = state["source_code"]
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return {**state, "missing": [], "error": str(e)}
    missing = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not ast.get_docstring(node) and node.body and node.lineno != node.end_lineno:
                code_block = ast.get_source_segment(source_code, node)
                if code_block:
                    missing.append({
                        "name": node.name,
                        "lineno": node.body[0].lineno,
                        "col_offset": node.body[0].col_offset,
                        "code_block": code_block
                    })
    return {**state, "missing": missing}


def generate_docstrings_node(state: Dict[str, Any]) -> Dict[str, Any]:
    missing = state["missing"]
    docstrings = []
    for item in missing:
        prompt = (
            "Please generate a concise, Google-style Python docstring for the following code.\n"
            "The docstring should explain the function's purpose, arguments, and what it returns.\n"
            "Do not include the function signature in your response, only the docstring content inside triple quotes.\n\n"
            f"Code:\n```python\n{item['code_block']}\n```"
        )
        try:
            response = model.generate_content(prompt)
            generated = response.text.strip()
            if generated.startswith('"""') and generated.endswith('"""'):
                generated = generated[3:-3].strip()
            elif generated.startswith("'''") and generated.endswith("'''"):
                generated = generated[3:-3].strip()
        except Exception:
            generated = ""
        docstrings.append({**item, "docstring": generated})
    return {**state, "docstrings": docstrings}


def insert_docstrings_node(state: Dict[str, Any]) -> Dict[str, Any]:
    lines = state["source_code"].splitlines()
    docstrings = state.get("docstrings", [])
    docstrings = sorted(docstrings, key=lambda x: x["lineno"], reverse=True)
    for item in docstrings:
        indent = " " * item["col_offset"]
        doc = item["docstring"]
        doc_lines = doc.split('\n')
        if len(doc_lines) == 1:
            formatted = f'{indent}"""{doc_lines[0]}"""'
        else:
            indented = "\n".join(f"{indent}{line}" for line in doc_lines)
            formatted = f'{indent}"""\n{indented}\n{indent}"""'
        lines.insert(item["lineno"] - 1, formatted)
    return {**state, "updated_code": "\n".join(lines)}


def write_file_node(state: Dict[str, Any]) -> Dict[str, Any]:
    output_path = state["output_path"]
    updated_code = state["updated_code"]
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(updated_code)
    return {**state, "status": "written"}


# --- LangGraph Build ---
def build_graph():
    g = StateGraph(State)
    g.add_node("read", read_file_node)
    g.add_node("parse", parse_missing_docstrings_node)
    g.add_node("generate", generate_docstrings_node)
    g.add_node("insert", insert_docstrings_node)
    g.add_node("write", write_file_node)
    g.add_edge("read", "parse")
    g.add_edge("parse", "generate")
    g.add_edge("generate", "insert")
    g.add_edge("insert", "write")
    g.add_edge("write", END)
    g.set_entry_point("read")
    return g.compile()


# --- Main Callable ---
def process_single_file(file_path: str, output_path: str) -> Dict[str, Any]:
    graph = build_graph()
    state = {"file_path": file_path, "output_path": output_path}
    return graph.invoke(state)
