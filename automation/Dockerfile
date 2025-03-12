FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1

# Install required packages
RUN apt-get update && apt-get install -y curl && \
    pip install watchdog requests python-telegram-bot==13.7 flask

# Copy the automation script
COPY automation.py /automation/automation.py

WORKDIR /automation

CMD ["python", "automation.py"]
