FROM python:3.12-slim

WORKDIR /app

# Install system dependencies if any (none required for now)
# RUN apt-get update && apt-get install -y ...

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose port (Render handles this via PORT env var, but 8001 is our local default)
EXPOSE 8001

# Command to run the application
CMD ["python", "main.py"]
