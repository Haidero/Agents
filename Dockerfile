# Use python 3.10 slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# build-essential for compiling some python packages
# git just in case
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage cache
COPY requirements.txt .

# Install dependencies
# Installing CPU versions of torch first to keep image smaller if no GPU needed, 
# but allowing standard install for compatibility.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose ports
# 8501 for Streamlit
EXPOSE 8501

# Default command (can be overridden in compose)
CMD ["streamlit", "run", "web_app.py", "--server.address=0.0.0.0"]
