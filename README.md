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

**File filtering:** Binary files, lock files, and dependency folders (`node_modules`, `venv`, etc.) are skipped as they add noise without helping the LLM understand the project.

**File prioritization:** High-signal files (`README.md`, `main.py`, `package.json`, etc.) are sent to the LLM first, ensuring the most informative content is always included.

**Context limit:** Total file content is capped at 12,000 characters (~3,000 tokens) with a 2,000 character cap per file, keeping the prompt well within GPT's context window.

**Shallow clone:** Repositories are cloned with `depth=1` so only the latest snapshot is downloaded, keeping the API fast regardless of repo history size.
