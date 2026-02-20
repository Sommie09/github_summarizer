import json
import os
from typing import List
import git
import tempfile
import shutil
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from openai import OpenAI
from pydantic import BaseModel

IGNORED_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build"}
IGNORED_EXTENSIONS = {".png", ".jpg", ".gif", ".svg", ".ico", ".pdf", ".zip", ".exe", ".pyc", ".lock"}
IGNORED_FILENAMES = {"package-lock.json", "yarn.lock", "poetry.lock", "Pipfile.lock"}
HIGH_PRIORITY = {"readme.md", "main.py", "app.py", "index.js", "package.json", "pyproject.toml", "requirements.txt", "dockerfile"}

# Load environment variables from .env
load_dotenv()

app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Handle exceptions
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"status": "error", "message": "Invalid request body. Please provide a 'github_url' field."}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "An unexpected error occurred on the server."}
    )


class RepoRequest(BaseModel):
    github_url: str

class RepoSummaryResponse(BaseModel):
    repository: str
    summary: str
    technologies: List[str]
    structure: str

class ErrorResponse(BaseModel):
    status: str = "error"
    message: str


# Structured error response
def error_response(status_code: int, message: str):
    raise HTTPException(
        status_code=status_code,
        detail={"status": "error", "message": message}
    )

# Parses github url
def parse_github_url(url: str):
    parts = url.rstrip("/").split("/")
    if "github.com" not in parts or len(parts) < 5:
        error_response(400, "Invalid GitHub URL format. Expected: https://github.com/owner/repo")
    owner = parts[-2]
    repo = parts[-1]
    return owner, repo

#Calls Github REST API
def fetch_repo_data(owner: str, repo: str):
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    response = requests.get(api_url)

    if response.status_code == 404:
        error_response(404, f"Repository '{owner}/{repo}' was not found on GitHub.")
    elif response.status_code != 200:
        error_response(502, "Failed to fetch repository data from GitHub. Try again later.")

    return response.json()

#Fetches raw github content
def fetch_readme(owner: str, repo: str):
    readme_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    headers = {"Accept": "application/vnd.github.v3.raw"}
    response = requests.get(readme_url, headers=headers)

    if response.status_code == 200:
        return response.text[:3000]
    return "No README available."

#Stores content in a temp file, loops to get priority files and caps character at 12,000.
def clone_and_fetch(github_url: str) -> str:
    tmp_dir = tempfile.mkdtemp()
    try:
        git.Repo.clone_from(github_url, tmp_dir, depth=1)
    except Exception:
        error_response(422, "Could not clone the repository. Make sure it's public and the URL is correct.")

    all_files = []
    for dirpath, dirnames, filenames in os.walk(tmp_dir):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for filename in filenames:
            if filename in IGNORED_FILENAMES or any(filename.endswith(e) for e in IGNORED_EXTENSIONS):
                continue
            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path, tmp_dir)
            is_priority = filename.lower() in HIGH_PRIORITY
            all_files.append((is_priority, rel_path, full_path))
            
    #Sort for high priority
    all_files.sort(key=lambda x: not x[0])

    # This ensures large repositiories are handled
    context = ""
    for _, rel_path, full_path in all_files:
        if len(context) >= 12000:
            break
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(2000)
            if content.strip():
                context += f"\n### {rel_path}\n{content}\n"
        except Exception:
            continue

    shutil.rmtree(tmp_dir)
    return context

def summarize_with_gpt(repo_data: dict, context: str):
    prompt = f"""
You are a helpful assistant. Analyze the following GitHub repository and respond ONLY with a valid JSON object — no extra text, no markdown, no code blocks.

Repository Name: {repo_data.get('name')}
Description: {repo_data.get('description', 'No description provided')}
Primary Language: {repo_data.get('language', 'Unknown')}
Stars: {repo_data.get('stargazers_count', 0)}
Forks: {repo_data.get('forks_count', 0)}
Open Issues: {repo_data.get('open_issues_count', 0)}

README (first 3000 characters):
{context}

Respond with this exact JSON structure:
{{
  "summary": "A concise human-readable summary of what the project does and who it's for.",
  "technologies": ["list", "of", "languages", "frameworks", "or", "tools", "used"],
  "structure": "A one or two sentence description of how the project's folders and files are organized."
}}
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600
    )
    return response.choices[0].message.content


#Routes
@app.get("/")
def root():
    return {"message": "GitHub Summarizer API is running!"}

@app.post("/summarize", response_model=RepoSummaryResponse)
def summarize_repo(request: RepoRequest):
    owner, repo = parse_github_url(request.github_url)
    repo_data = fetch_repo_data(owner, repo)
    context = clone_and_fetch(request.github_url)        
    raw_summary = summarize_with_gpt(repo_data, context)

    try:
        structured = json.loads(raw_summary)
    except json.JSONDecodeError:
        error_response(500, "The AI returned an unexpected response. Please try again.")

    return {
        "repository": f"{owner}/{repo}",
        **structured
    }