# lightweight Python base image
FROM python:3.11-slim

# set a few environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# define the working directory
WORKDIR /app

# install the system libraries the application needs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgomp1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# copy requirements.txt file
COPY requirements.txt .

# install the CPU-only version of PyTorch, 
# because this project is deployed in a CPU-based environment
# so this helps reduce the image size a lot
# install the remaining Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchvision && \
    pip install --no-cache-dir -r requirements.txt

# copy the web service source code and model file into the container
COPY main.py .
COPY best_model.pt .

# expose port 8000  
EXPOSE 8000

# set the application entry point with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]