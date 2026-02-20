# GitHub Repository Summarizer

A FastAPI service that takes a GitHub repository URL and returns a human-readable summary using GPT.

## Setup

1. Clone this repo and navigate into it:
```bash
   git clone https://github.com/Sommie09/github_summarizer.git
   cd github-summarizer
```

2. Create and activate a virtual environment:
```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
   pip install -r requirements.txt
```

4. Create a .env file and add your OpenAI API key 
```
   OPENAI_API_KEY=your_key_here
```

5. Run the server:
```bash
   uvicorn main:app --reload
```

6. Test it at `http://127.0.0.1:8000/docs`

## Design Decisions

**File filtering:** Binary files, lock files, and dependency folders (`node_modules`, `venv`, `.git`, etc.) are skipped as they add noise without helping the LLM understand the project. Files like `.png`, `.jpg`, `.exe`, and `.pyc` are also excluded as they are unreadable by the LLM and waste context space.

**File prioritization:** High-signal files (`README.md`, `main.py`, `app.py`, `package.json`, `requirements.txt`, `dockerfile`, etc.) are sorted to the front of the queue and sent to the LLM first. This ensures that even if the context budget runs out, the most informative files are always included.

**Context limit:** Total file content is capped at 12,000 characters (~3,000 tokens) with a 2,000 character cap per file. This keeps the prompt well within GPT's context window, prevents crashes on large repositories, and leaves enough room for the prompt instructions and the model's response.

**Shallow clone:** Repositories are cloned with `depth=1` so only the latest snapshot is downloaded without the full Git history. This keeps the API fast regardless of how long the repository has existed, and the temporary folder is deleted immediately after the context is collected.

**Error handling:** All errors return a consistent `{"status": "error", "message": "..."}` JSON shape with an appropriate HTTP status code. Specific cases handled include invalid URL format (400), repository not found (404), GitHub API failure (502), failed repository clone (422), unexpected GPT response (500), invalid request body (422), and any unhandled server error (500). API keys are never hardcoded — they are loaded from a `.env` file using `python-dotenv` and the `.env` file is excluded from version control via `.gitignore`.

**Testing:** Tests are written using `pytest` and FastAPI's built-in `TestClient`. Each error case is tested individually by sending deliberately bad input — an invalid URL, a non-existent repository, and a missing request field — and asserting that the response returns the correct status code and that the `status` field equals `"error"`. Tests can be run with `pytest test_main.py -v`.
