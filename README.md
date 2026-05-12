# Document Generation Agent

This project is a simple Document Generation Agent that scans a codebase folder and generates a High Level Design (HLD) document (.docx) using a template and an LLM. The implementation is intentionally minimal and clear.

## Project structure

- `backend/` - FastAPI backend and template files
  - `app/main.py` - FastAPI application (endpoints: `/api/generate`, `/download/{filename}`)
  - `app/llm.py` - LLM client abstraction (mock fallback). Configure `PROVIDER` and keys in `.env` for real providers.
  - `app/generator.py` - Scans folders, builds prompts, calls LLM, renders `.docx`.
  - `app/template/prompt.json` - Default HLD sections and instructions.
  - `app/template/hld_template.docx` - Created automatically on first run (if missing).
  - `requirements.txt` - Python dependencies
  - `.env.example` - example environment variables
- `frontend/` - Static frontend (served by FastAPI)
  - `index.html`, `app.js`, `styles.css`

## Quick start

1. Create a Python virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

2. Copy `.env.example` to `.env` and configure provider/keys if available. By default the server uses a mock LLM if no keys are set.

```bash
cp backend/.env.example backend/.env
# Edit backend/.env to set PROVIDER and keys if desired
```

3. Run the server:

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

4. Open the frontend in your browser:

Visit http://127.0.0.1:8000/ and enter the absolute path to the project or folder you want to generate an HLD for, then click "Generate HLD".

After generation completes you'll get a download link for a `.docx` file generated under `/tmp`.

## How it works

- The backend scans files under the provided folder path (limited snippets are read).
- The generator builds prompts for each section defined in `app/template/prompt.json` and sends them to the LLM client.
- The LLM client currently uses a safe mock fallback when `PROVIDER=mock` or keys are not configured. You can wire in real Google Gemini or Azure calls in `app/llm.py`.
- The outputs are assembled into a `.docx` file using `python-docx` and saved to `/tmp`.

## Template and prompts

Edit `backend/app/template/prompt.json` to change the default sections and instructions. The `generator` will create a `hld_template.docx` file from these prompts if it does not already exist.

## Customize LLM provider

- `backend/app/llm.py` contains a simple `LLMClient` class. Replace the mock implementation with calls to Google Gemini (PaLM) or Azure OpenAI as you prefer. Keep the `generate_text(prompt)` async signature.

## Notes

- No database is used; generated files are saved to `/tmp` and made available for download.
- This is a minimal, extendable scaffold intended to be clear and easy to adapt. Add authentication, rate-limiting, file size safeguards, and production-ready LLM integration for a production deployment.
