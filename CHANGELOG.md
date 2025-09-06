# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure with Poetry dependency management
- Multi-agent literature review system using AutoGen
- Streamlit web interface for interactive literature reviews
- arXiv integration for paper search and retrieval
- Professional development setup with ruff, mypy, pytest
- Pre-commit hooks for code quality enforcement
- Comprehensive test coverage configuration (95% target)
- CI/CD ready project structure
- Documentation overhaul: enhanced README with architecture diagram, Quickstart, troubleshooting
- CONTRIBUTING guide with branching, Conventional Commits, and workflow
- GitHub templates: PR template and issue templates (bug, feature)
- SECURITY policy and MIT LICENSE file

### Changed
- Restructured codebase into proper Python package layout
- Moved from simple scripts to modular package design
- Enhanced Streamlit UI with professional styling and UX improvements
- Updated required Python runtime to 3.12.11+
- Ruff target version set to Python 3.12

### Fixed
- Minor documentation inconsistencies

### Security
- Clarified vulnerability reporting process in SECURITY policy

### Changed
- Python 3.12.11 runtime target
- Poetry for dependency management
- Ruff for linting and formatting (PEP 8 compliance)
- mypy for strict type checking
- pytest with asyncio support for testing
- Coverage reporting with HTML and XML outputs


## [0.1.0] - 2024-09-01

### Added
- Initial project bootstrap
- Core AutoGen multi-agent backend
- Basic Streamlit frontend
- Literature review workflow implementation

### Known Limitations
- Streamlit UI minimal styling in initial release
- Limited export formats for reviews

### Roadmap
- Richer UI components and toasts
- Additional data sources beyond arXiv
- Configurable multi-agent strategies
