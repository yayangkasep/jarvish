FROM python:3.10-slim

WORKDIR /app

# Install the package itself (pulls in dependencies declared in pyproject.toml)
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# Run via the console-script entry point defined in pyproject.toml,
# so this stays correct even if the internal src/ layout changes.
CMD ["jarvish-server"]
