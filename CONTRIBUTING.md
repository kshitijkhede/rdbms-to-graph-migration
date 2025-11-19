# Contributing to RDBMS to Graph Migration System

Thank you for your interest in contributing to this project! This document provides guidelines for contributing.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/rdbms-to-graph-migration.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Run tests: `pytest tests/`
6. Commit your changes: `git commit -am 'Add some feature'`
7. Push to the branch: `git push origin feature/your-feature-name`
8. Create a Pull Request

## Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ --cov=src

# Format code
black src/ tests/

# Lint code
flake8 src/ tests/
```

## Code Style

- Follow PEP 8 style guide
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions small and focused
- Write unit tests for new features

## Testing

- Write unit tests for all new functionality
- Ensure all tests pass before submitting PR
- Aim for >80% code coverage
- Include integration tests for major features

## Pull Request Guidelines

- Update documentation for any changed functionality
- Add tests for new features
- Ensure CI/CD pipeline passes
- Keep PRs focused on a single feature or fix
- Write clear commit messages

## Reporting Issues

When reporting issues, please include:
- Description of the problem
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, Python version, database versions)
- Error messages and logs

## Feature Requests

We welcome feature requests! Please:
- Check if the feature already exists
- Clearly describe the use case
- Explain why it would be useful
- Consider contributing the implementation

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Help others learn and grow

## Questions?

Feel free to open an issue for any questions or discussions.

Thank you for contributing!
