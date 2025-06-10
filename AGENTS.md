# Development Guidelines

To run the project's automated checks and optional commands, follow these steps:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt pytest
   ```
2. If you want to run API endpoints, set `OPENROUTER_API_KEY` in the environment or create a file named `.openrouter_key` containing the key.
3. Run the test suite:
   ```bash
   PYTHONPATH=. pytest -q
   ```
4. You can optionally start the backend for manual or agent interactions using:
   ```bash
   python start_backend.py
   # or
   python start_empresa.py
   ```

The tests do not need network access because OpenRouter calls are mocked.
