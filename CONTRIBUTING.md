# Contributing

Thank you for your interest in this project! This is a portfolio/demo project, but contributions and suggestions are welcome.

## Getting Started

1. Fork the repository
2. Clone your fork and set up the environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Development Workflow

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Run tests: `pytest tests/ -v`
4. Run linting: `ruff check src/ tests/`
5. Commit with a descriptive message
6. Push and open a Pull Request

## Code Standards

- **Python**: Follow PEP 8, enforced by Ruff
- **SQL**: Uppercase keywords, lowercase identifiers
- **Terraform**: `terraform fmt` before committing
- **Tests**: Maintain or improve coverage (target: 60%+)

## Reporting Issues

Open a GitHub issue with:
- Steps to reproduce
- Expected vs. actual behavior
- Python version and OS

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
