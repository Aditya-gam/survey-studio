# Survey Studio 📚

A multi-agent literature review assistant powered by AutoGen and Streamlit. Survey Studio uses AI agents to automatically search arXiv, analyze research papers, and generate comprehensive literature reviews.

![Python](https://img.shields.io/badge/python-3.11.9+-blue.svg)
![Poetry](https://img.shields.io/badge/dependency--management-poetry-blue)
![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)
![Type Checker: mypy](https://img.shields.io/badge/type--checker-mypy-blue)
![Coverage](https://img.shields.io/badge/coverage-95%25-green)

## 🌟 Features

- **Multi-Agent System**: Two specialized AI agents work together:
  - **Search Agent** 🔍: Crafts optimized arXiv queries and retrieves relevant papers
  - **Summarizer Agent** 📝: Generates structured literature reviews with key insights
- **Interactive Web Interface**: Clean, professional Streamlit UI with real-time conversation streaming
- **arXiv Integration**: Direct access to the world's largest repository of academic papers
- **Configurable**: Adjustable number of papers, AI models, and search parameters
- **Professional Development Setup**: Full CI/CD pipeline with testing, linting, and type checking

## 🚀 Quick Start

### Prerequisites

- Python 3.11.9+
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

1. **Activate the virtual environment:**
   ```bash
   poetry shell
   ```

2. **Run the development server:**
   ```bash
   streamlit run streamlit_app.py
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

- **Mypy missing imports**: add stubs or packages to the mypy hook `additional_dependencies` in `.pre-commit-config.yaml`.
- **Hooks keep reformatting files**: run `poetry run ruff format .` then re-run `pre-commit`. Ensure your editor doesn’t trim/convert line endings unexpectedly.
- **Pre-commit cache issues**: try `poetry run pre-commit clean` and `poetry run pre-commit gc`.
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
│   └── workflows/             # CI/CD workflows (future)
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
# Run all tests
poetry run pytest

# Run with coverage report
poetry run pytest --cov=src/survey_studio --cov-report=html

# Run specific test file
poetry run pytest tests/test_backend.py
```

## 📋 Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)

### Streamlit Configuration

The `.streamlit/config.toml` file contains UI theme and server settings.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests and linting: `poetry run pytest && poetry run ruff check .`
5. Commit your changes: `git commit -m 'feat: add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

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
- **CI/CD**: Pre-commit hooks, GitHub Actions (planned)

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
