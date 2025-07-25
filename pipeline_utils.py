from docstring_generator import build_graph
from google.generativeai import GenerativeModel
from pathlib import Path

def process_file_docstring_and_comment(input_path: Path, output_path: Path, model: GenerativeModel):
    # Step 1: Insert docstrings using LangGraph
    graph = build_graph()
    state = {
        "file_path": str(input_path),
        "output_path": str(output_path)
    }
    result = graph.invoke(state)
    code_with_docstrings = result.get("updated_code")

    if not code_with_docstrings:
        raise ValueError(f"Failed to insert docstrings in {input_path.name}")

    # Step 2: Ask Gemini to add line-by-line comments
    prompt = (
        "Add clear, concise, and line-by-line comments to the following Python code. "
        "Only return the commented code:\n\n"
        f"{code_with_docstrings}"
    )
    response = model.generate_content(prompt)
    final_code = response.text.strip()

    # Step 3: Save the final file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_code)
