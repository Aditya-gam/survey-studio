# Survey Studio 📚

A multi-agent literature review assistant powered by AutoGen and Streamlit. Survey Studio uses AI agents to automatically search arXiv, analyze research papers, and generate comprehensive literature reviews.

[![Python](https://img.shields.io/badge/python-3.12.11+-blue.svg)](https://www.python.org/downloads/release/python-31211/)
[![Poetry](https://img.shields.io/badge/poetry-managed-1f5fff.svg)](https://python-poetry.org/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://docs.astral.sh/ruff/)
[![mypy](https://img.shields.io/badge/type--checker-mypy-blue)](https://mypy-lang.org/)
[![CI](https://github.com/survey-studio/survey-studio/workflows/CI/badge.svg)](https://github.com/survey-studio/survey-studio/actions)
[![Coverage](https://codecov.io/gh/survey-studio/survey-studio/branch/main/graph/badge.svg)](https://codecov.io/gh/survey-studio/survey-studio)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Commitizen friendly](https://img.shields.io/badge/commitizen-friendly-brightgreen.svg)](https://commitizen-tools.github.io/commitizen/)

## 🌟 Features

- **Multi-Agent System**: Two specialized AI agents work together:
  - **Search Agent** 🔍: Crafts optimized arXiv queries and retrieves relevant papers
  - **Summarizer Agent** 📝: Generates structured literature reviews with key insights
- **Interactive Web Interface**: Clean, professional Streamlit UI with real-time conversation streaming
- **arXiv Integration**: Direct access to the world's largest repository of academic papers
- **Configurable**: Adjustable number of papers, AI models, and search parameters
- **Professional Development Setup**: Full CI/CD pipeline with testing, linting, and type checking

## 🧭 Architecture

```mermaid
flowchart TD
  subgraph UI["Streamlit UI"]
    User["User"] -->|"inputs topic, params"| Sidebar["Sidebar Controls"]
    Chat["Chat Panel"] -->|"streams responses"| User
  end

  subgraph Backend["Survey Studio Orchestrator"]
    Orchestrator["Orchestrator"] --> SearchAgent
    Orchestrator --> SummarizerAgent
  end

  SearchAgent["Search Agent"] -->|"queries"| ArXiv[("arXiv API")]
  SearchAgent -->|"returns papers"| Orchestrator
  SummarizerAgent["Summarizer Agent"] -->|"LLM calls"| OpenAI[("OpenAI API")]
  Orchestrator -->|"updates"| UI
```

- **Streamlit UI**: Collects user input, renders agent conversation and results.
- **Search Agent**: Generates and executes arXiv queries.
- **Summarizer Agent**: Produces structured review using OpenAI models.
- **Orchestrator**: Manages the multi-agent loop and data flow.

## 🖼 Screenshots & Media

- Placeholder: Streamlit sidebar and chat view (add screenshots here)
- Placeholder: End-to-end GIF of literature review workflow

## 🚀 Quick Start

### Prerequisites

- Python 3.12.11+
- Poetry (for dependency management)
- OpenAI API key

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/survey-studio/survey-studio.git
   cd survey-studio
   ```

2. **Install dependencies with Poetry:**
   ```bash
   poetry install
   ```

3. **Set up environment variables:**
   ```bash
   export OPENAI_API_KEY="your-openai-api-key-here"
   ```

4. **Run the application:**
   ```bash
   poetry run streamlit run streamlit_app.py
   ```

The application will open in your browser at `http://localhost:8501`.

### Secrets Management

- Local: create `.streamlit/secrets.toml`
  ```toml
  OPENAI_API_KEY = "your-openai-api-key-here"
  ```
- In code, read via `st.secrets["OPENAI_API_KEY"]` or environment variable.

### Deploy to Streamlit Community Cloud

1. Push the repository to GitHub.
2. Go to Streamlit Community Cloud and create a new app from the repo.
3. Set `OPENAI_API_KEY` in the app Secrets.
4. Deploy. The app will build with Poetry and start automatically.

### Local Port Configuration

Specify a custom port if 8501 is busy:

```bash
poetry run streamlit run streamlit_app.py --server.port 8502
```

## 🛠 Development Setup

### Initial Setup

1. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Clone and install dependencies:**
   ```bash
   git clone https://github.com/survey-studio/survey-studio.git
   cd survey-studio
   poetry install
   ```

3. **Install pre-commit hooks:**
   ```bash
   poetry run pre-commit install
   ```

4. **(Optional) Prime hook environments:** this can speed up the first commit
   ```bash
   poetry run pre-commit install --install-hooks
   ```

### Development Workflow

1. **No venv activation required (use Poetry runner):**
   ```bash
   # Prefer prefixing commands with 'poetry run'
   poetry run <command>
   ```

2. **Run the development server (custom port optional):**
   ```bash
   poetry run streamlit run streamlit_app.py --server.port 8501
   ```

3. **Run tests:**
   ```bash
   poetry run pytest
   ```

4. **Run linting and formatting:**
   ```bash
   poetry run ruff check .
   poetry run ruff format .
   ```

5. **Type checking:**
   ```bash
   poetry run mypy src/
   ```

6. **Pre-commit: run the full code quality pipeline locally:**
   ```bash
   poetry run pre-commit run --all-files
   ```
   - Runs in this order: detect-secrets → repo hygiene checks → ruff-format → ruff (with --fix) → mypy → poetry-check → poetry-lock
   - Commit message validation (Commitizen) runs on `commit-msg` and is enforced during `git commit`

### Code Quality Pipeline

The project enforces 100% compliance via Ruff, mypy, detect-secrets, and commit message validation.

- **Ruff formatting**: opinionated code formatting. Imports sorted with isort profile.
- **Ruff linting**: rule sets enabled: E,W,F,I,B,C4,UP,N,SIM,TCH,ARG,PIE,PT,RET,SLF,TID,ERA,PL.
- **Type checking (mypy)**: strict configuration; 3rd-party types installed via hook deps.
- **Secrets scanning**: `detect-secrets` with a committed baseline.
- **Commit messages**: Conventional Commits validated by Commitizen.
- **Poetry checks**: validates project metadata and lock consistency.

Per-file ignores are configured to reduce noise:
- `__init__.py`: ignore `F401` (re-export patterns)
- `tests/**/*`: ignore `N806` (naming in tests)

### Secrets Scanning

- Baseline file: `.secrets.baseline` (committed)
- Update baseline after meaningful changes:
  ```bash
  poetry run detect-secrets scan > .secrets.baseline
  git add .secrets.baseline
  git commit -m "chore(security): update detect-secrets baseline"
  ```
- Exclusions: test data and fixtures are excluded by default in the hook.

### Commit Messages (Conventional Commits)

- Use Commitizen to guide commit messages:
  ```bash
  poetry run cz commit
  ```
- Validate an existing message:
  ```bash
  poetry run cz check --message "feat: add new exporter"
  ```

### Troubleshooting

- **Poetry not found / path issues**:
  - Install: `curl -sSL https://install.python-poetry.org | python3 -`
  - Ensure Poetry is on PATH. On macOS (zsh): add `export PATH="$HOME/.local/bin:$PATH"` to `~/.zshrc`.
- **Python 3.12.11 not available**:
  - Install via `pyenv`: `pyenv install 3.12.11 && pyenv local 3.12.11`
  - Recreate env: `poetry env use 3.12 && poetry install`
- **Dependency resolution failures**:
  - `poetry lock --no-update` then `poetry install --sync`
  - Clear cache: `poetry cache clear pypi --all`
- **Streamlit port already in use**:
  - Run on a new port: `poetry run streamlit run streamlit_app.py --server.port 8502`
  - Or set in `.streamlit/config.toml` under `[server] port = 8502`
- **OpenAI API key not detected**:
  - Ensure `OPENAI_API_KEY` is exported in your shell profile and available to the app
  - For Streamlit Cloud, set in app Secrets
- **Mypy missing imports**:
  - Add stubs or packages to mypy hook `additional_dependencies` in `.pre-commit-config.yaml`
- **Pre-commit keeps changing files**:
  - Run `poetry run ruff format .` then `poetry run pre-commit run --all-files`
- **Commit message rejected** (Conventional Commits):
  - Use Commitizen: `poetry run cz commit`

### CI Validation Locally

You can simulate the GitHub Actions workflow locally using `act`:

```bash
# Install act (macOS with brew)
brew install act

# Run the CI workflow locally (uses default container runners)
act -j lint
act -j type
act -j test

# Pass Codecov token for local runs if needed
CODECOV_TOKEN=your_token act -j test
```

Common CI issues and resolutions:
- Missing Poetry: ensure the workflow installs the pinned Poetry version.
- Coverage below 95%: add or improve tests; check exclusions in `pyproject.toml`.
- Mypy import errors: add stubs or dependencies under mypy hook `additional_dependencies`.
- **Secrets false positives**: update the baseline after verifying the match is benign.

### Hook Order and Idempotency

- Hooks are ordered to auto-fix first, then validate. A second run of `pre-commit run --all-files` should produce no changes.


### Project Structure

```
survey-studio/
├── src/
│   └── survey_studio/
│       ├── __init__.py          # Package initialization
│       ├── app.py              # Streamlit frontend
│       └── backend.py          # AutoGen multi-agent backend
├── tests/                      # Test suite
├── .streamlit/
│   └── config.toml            # Streamlit configuration
├── .github/
│   └── workflows/             # CI/CD workflows
├── pyproject.toml             # Poetry configuration
├── .pre-commit-config.yaml    # Pre-commit hooks
├── .gitignore                 # Git ignore rules
├── CHANGELOG.md               # Project changelog
├── README.md                  # This file
└── streamlit_app.py          # Entry point
```

## 📖 Usage

### Web Interface

1. Launch the Streamlit app
2. Enter your research topic in the sidebar
3. Adjust the number of papers (1-10)
4. Select the AI model
5. Click "Start Review" to begin

### Programmatic Usage

```python
import asyncio
from survey_studio import run_survey_studio

async def example():
    async for message in run_survey_studio(
        topic="transformer architectures",
        num_papers=5,
        model="gpt-4o-mini"
    ):
        print(message)

asyncio.run(example())
```

## 🧪 Testing

The project uses pytest with comprehensive test coverage:

```bash
# Run all tests with configured coverage and 95% threshold
poetry run pytest

# Generate coverage HTML locally (outputs to htmlcov/)
poetry run pytest --cov-report=html

# Run specific test file
poetry run pytest tests/unit/test_tools.py
```

### Coverage Reporting

- The project enforces a 95% coverage threshold via `pyproject.toml` (`--cov-fail-under=95`).
- CI uploads coverage to Codecov. View the report on your repo’s Codecov page.
- Local artifacts: `htmlcov/index.html` for an interactive report, `coverage.xml` for CI tools.

### CI/CD

- GitHub Actions runs three jobs on push/PR: Lint (Ruff), Type (mypy), Test (pytest+coverage).
- Coverage is uploaded to Codecov, and the CI enforces the 95% threshold.
- Badges: CI and Coverage appear at the top of this README.

## 📋 Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)

### Streamlit Configuration

The `.streamlit/config.toml` file contains UI theme and server settings.

### CI/Codecov Setup

1. Add GitHub secret `CODECOV_TOKEN` with your repository token from Codecov.
2. Install the Codecov GitHub App on the repository and enable status checks.
3. Ensure required status checks include: `Lint (Ruff)`, `Type Check (mypy)`, `Test (pytest + coverage)`, and `codecov/project`, `codecov/patch`.
4. Branch protection: require pull request reviews, dismiss stale approvals on new commits, and enforce linear history (rebase merges).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/amazing-feature`
3. Make your changes
4. Run tests and linting: `poetry run pytest && poetry run ruff check .`
5. Commit your changes: `git commit -m 'feat: add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request (rebase merge strategy, no merge commits). See `CONTRIBUTING.md` for details.

### Commit Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code formatting
- `refactor:` Code refactoring
- `test:` Test additions or updates
- `chore:` Build process or tooling changes

## 📊 Technology Stack

- **Backend**: AutoGen (multi-agent framework)
- **Frontend**: Streamlit (web interface)
- **Data Source**: arXiv API
- **AI Models**: OpenAI GPT (configurable)
- **Development**: Poetry, Ruff, mypy, pytest
- **CI/CD**: Pre-commit hooks, GitHub Actions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [AutoGen](https://github.com/microsoft/autogen) for the multi-agent framework
- [Streamlit](https://streamlit.io/) for the web interface framework
- [arXiv](https://arxiv.org/) for providing access to academic papers
- [OpenAI](https://openai.com/) for the language models

## 📞 Support

If you have questions or need help:

1. Check the [documentation](https://github.com/survey-studio/survey-studio/wiki)
2. Search [existing issues](https://github.com/survey-studio/survey-studio/issues)
3. Create a [new issue](https://github.com/survey-studio/survey-studio/issues/new)

---

**Survey Studio** - Accelerating research through AI-powered literature reviews ✨
