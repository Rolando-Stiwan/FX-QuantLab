FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir -e .

COPY data/ data/
COPY start.sh .
RUN sed -i 's/\r$//' start.sh
RUN chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]