# pytestbox itself: the tool that sandboxes other people's test suites.
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir .

CMD ["pytestbox", "--help"]
