# Contributing to YTDownloader

We love receiving contributions from the community, and we're thrilled that you're interested in making YTDownloader even better!

There are many ways to contribute, from reporting bugs and suggesting new features to writing code and improving the documentation.

## How to Contribute

### Reporting Bugs

If you encounter a bug, please [open an issue](https://github.com/your-username/ytdownloader/issues) and provide as much detail as possible, including:

-   A clear and descriptive title
-   Steps to reproduce the bug
-   The expected behavior and what actually happened
-   Your operating system and Python version

### Suggesting Enhancements

If you have an idea for a new feature or an improvement to an existing one, please [open an issue](https://github.com/your-username/ytdownloader/issues) to discuss it. This allows us to give you feedback and ensure that your suggestion aligns with the project's goals.

### Submitting Pull Requests

If you'd like to contribute code, please follow these steps:

1.  **Fork the Repository**: Create a fork of the repository to your own GitHub account.

2.  **Clone Your Fork**:
    ```bash
    git clone https://github.com/your-username/ytdownloader.git
    cd ytdownloader
    ```

3.  **Create a New Branch**:
    ```bash
    git checkout -b your-feature-branch
    ```

4.  **Set Up Your Development Environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

5.  **Make Your Changes**: Write your code and make sure it follows the existing style.

6.  **Run the Tests**:
    ```bash
    python -m unittest discover tests
    ```

7.  **Commit Your Changes**:
    ```bash
    git commit -m "Your descriptive commit message"
    ```

8.  **Push to Your Fork**:
    ```bash
    git push origin your-feature-branch
    ```

9.  **Open a Pull Request**: Go to the original repository and open a pull request.

## Coding Style

Please follow the existing coding style in the project. We use [PEP 8](https://www.python.org/dev/peps/pep-0008/) as a general guideline.

We look forward to your contributions!
