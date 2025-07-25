# project_documenter.py
# This module generates documentation and comments for Python files in a project directory.
import os
# import shutil


def comment_python_files(folder_path, model, output_dir="commented_files"):
    os.makedirs(output_dir, exist_ok=True)
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                with open(full_path, "r", encoding="utf-8") as f:
                    code = f.read()
                prompt = (
                    "Add clear, concise, and line-by-line comments to the following Python code. "
                    "Return only the commented code:\n\n"
                    f"{code}"
                )
                response = model.generate_content(prompt)
                rel_dir = os.path.relpath(root, folder_path)
                out_dir = os.path.join(output_dir, rel_dir)
                os.makedirs(out_dir, exist_ok=True)
                out_path = os.path.join(out_dir, f"{os.path.splitext(file)[0]}_commented.py")
                with open(out_path, "w", encoding="utf-8") as out_f:
                    out_f.write(response.text)

def generate_project_documentation(folder_path, model, output_file="GENERATED_README.md"):
    file_summaries = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(('.py', '.txt', '.md', '.json', '.js', '.html', '.css')):
                try:
                    full_path = os.path.join(root, file)
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()[:3000]
                    rel_path = os.path.relpath(full_path, folder_path)
                    file_summaries.append(f"\n---\n### File: `{rel_path}`\n```text\n{content}\n```\n")
                except:
                    continue
    prompt = (
        "You are a senior software engineer and documentation expert.\n"
        "Generate a clean, structured README-style documentation for this project:\n"
        + "".join(file_summaries)
    )
    response = model.generate_content(prompt)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(response.text)
