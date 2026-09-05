import os
import sys

from reviewer.analyzer import ReviewEngine
from reviewer.diff_parser import DiffParser
from reviewer.llm_client import GeminiClient
from reviewer.config import ReviewSettings
from reviewer.github_client import GitHubClient

repo = os.getenv('GITHUB_REPOSITORY', '')
pr_number = os.getenv('PR_NUMBER', '')
if not repo or not pr_number:
    print('Skipping AI review outside PR context.')
    sys.exit(0)

owner, repo_name = repo.split('/', 1)
github_token = os.getenv('GITHUB_TOKEN', '')

# Create Gemini client from GitHub Actions secret
api_key = os.getenv('GEMINI_API_KEY', '').strip()
if api_key:
    settings = ReviewSettings()
    llm_client = GeminiClient(api_key=api_key, model=settings.gemini_model)
else:
    llm_client = None
    print('WARNING: GEMINI_API_KEY not set; review will use static analysis only')

client = GitHubClient(token=github_token)
files = client.get_changed_files(owner, repo_name, int(pr_number))
paths = [entry.get('filename', '') for entry in files]
raw_diff = client.get_diff(owner, repo_name, int(pr_number))
filtered_paths = DiffParser.filter_irrelevant_files(paths)

engine = ReviewEngine(llm_client=llm_client)
result = engine.analyze_diff(raw_diff, filtered_paths)
summary = result.summary
if result.findings:
    body = summary + '\n\n' + '\n'.join(
        f"- {item.title} ({item.severity}) in {item.file or 'unknown'}" for item in result.findings[:5]
    )
else:
    body = summary
client.create_review(owner, repo_name, int(pr_number), body)
print('AI review posted successfully.')