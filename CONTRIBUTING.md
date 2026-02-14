# Contributing to StreamCatch

Thank you for your interest in contributing to StreamCatch! We welcome community contributions. This document provides guidelines and instructions for contributing.

## Code of Conduct

Please note that this project is released with a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

## Ways to Contribute

### Reporting Bugs

Found a bug? Please help us fix it by [opening an issue](https://github.com/AmirrezaFarnamTaheri/YTDownloader/issues) with:

- **Clear title**: "Bug: Issue description"
- **Reproduction steps**: How to reliably reproduce the issue
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Environment**:
  - Operating System (Windows/macOS/Linux)
  - Python version (`python --version`)
  - Application version
- **Error details**: Include output from `ytdownloader.log` or `~/.streamcatch/app.log` if available
- **Screenshots**: Visual issues are helpful to include

### Suggesting Features

Have an idea for improvement? [Open an issue](https://github.com/AmirrezaFarnamTaheri/YTDownloader/issues) with:

- **Clear title**: "Feature: Brief description"
- **Use case**: Why would this be useful?
- **Proposed solution**: How should it work?
- **Alternatives**: Any other approaches considered?

### Submitting Code Changes

#### Setup Development Environment

1. **Fork the repository** on GitHub.
2. **Clone your fork** (or clone upstream directly):
   ```bash
   git clone https://github.com/<your-username>/YTDownloader.git
   # or:
   # git clone https://github.com/AmirrezaFarnamTaheri/YTDownloader.git
   cd YTDownloader
   ```
3. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Create a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
5. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

#### Making Changes

1. **Make your changes** following the coding standards (see below).
2. **Add/update tests** for your changes:
   ```bash
   pytest -v
   ```
3. **Check code quality**:
   ```bash
   black .
   isort .
   pylint $(git ls-files '*.py')
   ```
4. **Update documentation** if needed (README, docstrings, etc.).
5. **Verify everything works**:
   ```bash
   python main.py
   pytest
   ```

#### Submitting a Pull Request

1. **Push your changes**:
   ```bash
   git push origin feature/your-feature-name
   ```
2. **Create a Pull Request** on GitHub with:
   - **Title**: Clear, descriptive title
   - **Description**: Explain what changes were made and why
   - **Related issues**: Reference any related issues (#123)
   - **Screenshots**: If UI changes were made
3. **Respond to feedback** - Maintainers will review and suggest changes if needed.

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) standards.
- Use 4 spaces for indentation (not tabs).
- Maximum line length: 88 characters.
- Use type hints for function signatures.
- Write docstrings for all public functions/classes.

### Naming Conventions

- **Functions/Methods**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_CASE`
- **Private methods**: `_leading_underscore`

### Documentation

- Include docstrings with Args, Returns, Raises sections.
- Update docstrings when modifying functions.
- Include inline comments for complex logic.
- Update README/CHANGELOG for user-facing changes.

### Testing Requirements

- Write unit tests for new functionality.
- Maintain or improve test coverage.
- Run the full test suite before submitting PRs.

### Commit Messages

Write clear, concise commit messages:

```
Add feature: Brief description

Longer explanation of what was changed and why, if needed.
Keep the subject line to 50 characters.
```

- Use imperative mood ("Add feature" not "Added feature").
- Reference issues when relevant: "Fixes #123".
- Keep the first line under 50 characters.

## Project Structure

```
YTDownloader/
|-- main.py
|-- app_state.py
|-- app_controller.py
|-- app_layout.py
|-- ui_manager.py
|-- config_manager.py
|-- history_manager.py
|-- queue_manager.py
|-- tasks.py
|-- downloader/
|   |-- core.py
|   |-- info.py
|   |-- engines/
|   |-- extractors/
|-- views/
|   |-- download_view.py
|   |-- queue_view.py
|   |-- history_view.py
|   |-- rss_view.py
|   |-- settings_view.py
|-- tests/
|-- scripts/
|-- .github/
|-- wiki/
```

## Questions?

- Check [README.md](README.md) for documentation.
- Look at existing [issues](https://github.com/AmirrezaFarnamTaheri/YTDownloader/issues).
- Join discussions in issue comments.

Thank you for making StreamCatch better!
