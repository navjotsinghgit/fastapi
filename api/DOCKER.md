Docker image build and push

This project includes a `Dockerfile` for building a container image of the FastAPI app.

Build and push locally (PowerShell):

1. Login to Docker Hub:

```powershell
docker login
```

2. Build and push using the helper script (defaults to `23cs132/pro:latest`):

```powershell
# From project root
.\build-and-push.ps1 -ImageName 23cs132/pro -Tag latest
```

Notes:
- The script assumes you have Docker Desktop / Docker CLI installed and logged in.
- If you prefer manual commands, you can run:

```powershell
docker build -t 23cs132/pro:latest .
docker push 23cs132/pro:latest
```

CI/CD option:
- A GitHub Actions workflow is included at `.github/workflows/publish-image.yml`. To use it, set `DOCKER_USERNAME` and `DOCKER_PASSWORD` secrets in your repository settings. The workflow will build and push `23cs132/pro:latest` when changes are pushed to `main`.
