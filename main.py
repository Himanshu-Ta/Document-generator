from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from pathlib import Path
import shutil, os, zipfile, uuid, io

from gemini_utils import configure_gemini
from project_documenter import generate_project_documentation
from pipeline_utils import process_file_docstring_and_comment

app = FastAPI(title="Unified AI Project Processor")
BASE_DIR = Path(__file__).parent.resolve()
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

model = configure_gemini()

def extract_zip(zip_path: Path, extract_to: Path):
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)

def zip_folder_to_bytesio(source_dir: Path) -> io.BytesIO:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                zipf.write(file_path, file_path.relative_to(source_dir))
    zip_buffer.seek(0)
    return zip_buffer

@app.post("/process-project/")
async def process_project(file: UploadFile = File(...)):
    try:
        uid = str(uuid.uuid4())
        zip_path = TEMP_DIR / f"{uid}.zip"
        src_dir = TEMP_DIR / f"{uid}_src"
        final_dir = TEMP_DIR / f"{uid}_final"
        zip_output_dir = TEMP_DIR / f"{uid}_out"

        for d in [src_dir, final_dir, zip_output_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Save and extract ZIP
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        extract_zip(zip_path, src_dir)

        # Process each .py file (docstring + comment)
        py_files = list(src_dir.rglob("*.py"))
        for py_file in py_files:
            rel_path = py_file.relative_to(src_dir)
            out_file = final_dir / rel_path
            process_file_docstring_and_comment(py_file, out_file, model)

        # Generate README from original source
        readme_path = zip_output_dir / "README.md"
        generate_project_documentation(str(src_dir), model, output_file=readme_path)

        # Assemble final folder
        shutil.copytree(final_dir, zip_output_dir / "final_files")
        shutil.copy(readme_path, zip_output_dir / "final_files" / "README.md")

        # Zip and return
        zip_stream = zip_folder_to_bytesio(zip_output_dir)
        return StreamingResponse(
            zip_stream,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=processed_project.zip"}
        )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
