FROM python:3.13-slim

# Install dependencies for .NET
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    libicu-dev \
    && rm -rf /var/lib/apt/lists/*

# Install .NET 8.0 runtime using the official install script
RUN wget https://dot.net/v1/dotnet-install.sh -O dotnet-install.sh \
    && chmod +x dotnet-install.sh \
    && ./dotnet-install.sh --channel 8.0 --runtime dotnet --install-dir /usr/share/dotnet \
    && rm dotnet-install.sh \
    && ln -s /usr/share/dotnet/dotnet /usr/bin/dotnet

ENV DOTNET_ROOT=/usr/share/dotnet

WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev
COPY . .
EXPOSE 8000
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
