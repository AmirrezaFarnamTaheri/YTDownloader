# Contributing to StreamCatch

Thank you for your interest in contributing to StreamCatch! We welcome contributions from the community. This document provides guidelines and instructions for contributing.

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
- **Error details**: Include output from `ytdownloader.log` if available
- **Screenshots**: Visual issues are helpful to include

### Suggesting Features

Have an idea for improvement? [Open an issue](https://github.com/AmirrezaFarnamTaheri/YTDownloader/issues) with:

- **Clear title**: "Feature: Brief description"
- **Use case**: Why would this be useful?
- **Proposed solution**: How should it work?
- **Alternatives**: Any other approaches considered?

### Submitting Code Changes

#### Setup Development Environment

1. **Fork the Repository** on GitHub

2. **Clone your fork**:
   ```bash
   git clone https://github.com/your-username/StreamCatch.git
   cd StreamCatch
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
   ```

#### Making Changes

1. **Make your changes** following the coding standards (see below)

2. **Add/update tests** for your changes:
   ```bash
   # Run tests
   python -m unittest discover -s tests -p "test_*.py" -v
   ```

3. **Check code quality** (optional):
   ```bash
   # Format code
   black main.py downloader.py tests/

   # Type checking
   mypy main.py downloader.py

   # Linting
   pylint main.py downloader.py
   ```

4. **Update documentation** if needed (README, docstrings, etc.)

5. **Verify everything works**:
   ```bash
   # Run the app
   python main.py

   # Run full test suite
   python -m unittest discover -s tests -p "test_*.py" -v
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

3. **Respond to feedback** - Maintainers will review and suggest changes if needed

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) standards
- Use 4 spaces for indentation (not tabs)
- Maximum line length: 100 characters
- Use type hints for function signatures
- Write docstrings for all public functions/classes

### Naming Conventions

- **Functions/Methods**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_CASE`
- **Private methods**: `_leading_underscore`

### Documentation

- Include docstrings with Args, Returns, Raises sections:
  ```python
  def download_video(url: str, output_path: str = '.') -> None:
      """
      Download a video from the given URL.

      Args:
          url: The URL of the video to download.
          output_path: Directory to save the file (default: current directory).

      Raises:
          ValueError: If the URL is invalid.
          DownloadError: If the download fails.
      """
  ```

- Update docstrings when modifying functions
- Include inline comments for complex logic
- Update README/CHANGELOG for user-facing changes

### Testing Requirements

- Write unit tests for new functionality
- Maintain or improve test coverage
- Run full test suite before submitting PR:
  ```bash
  python -m unittest discover -s tests -p "test_*.py" -v
  ```

- Test edge cases and error handling
- Mock external dependencies (yt-dlp, HTTP requests, etc.)

### Commit Messages

Write clear, concise commit messages:

```
Add feature: Brief description

Longer explanation of what was changed and why, if needed.
Keep the subject line to 50 characters.
```

- Use imperative mood ("Add feature" not "Added feature")
- Reference issues when relevant: "Fixes #123"
- Keep first line under 50 characters
- Add detail in body if needed

## Project Structure

```
StreamCatch/
├── main.py                # GUI implementation (Flet)
├── downloader.py          # Core download logic
├── components.py          # UI components
├── config_manager.py      # Configuration management
├── history_manager.py     # History management
├── queue_manager.py       # Download queue management
├── requirements.txt       # Python dependencies
├── tests/                 # Test suite
└── docs/
    ├── README.md          # User documentation
    ├── CONTRIBUTING.md    # This file
    └── CODE_OF_CONDUCT.md # Community guidelines
```

## Questions?

- Check [README.md](README.md) for documentation
- Look at existing [issues](https://github.com/AmirrezaFarnamTaheri/YTDownloader/issues)
- Join discussions in issue comments

## Recognition

Contributors will be recognized in:
- The CONTRIBUTORS file
- Release notes for features/bug fixes
- GitHub contributors page

Thank you for making StreamCatch better! 🎉
