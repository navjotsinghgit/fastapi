@echo off
REM Alternative deployment using existing Python image (Windows)
echo 🐳 CarbonTracker API - Alternative Deployment (No Build Required)

REM Create a simple run script that mounts your code
docker run -d ^
  --name carbontracker-api ^
  --restart unless-stopped ^
  -p 8000:8000 ^
  -v "%cd%:/app" ^
  -w /app ^
  -e PYTHONPATH=/app ^
  python:3.11-slim ^
  bash -c "apt-get update && apt-get install -y curl && pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000"

if %ERRORLEVEL% equ 0 (
    echo ✅ CarbonTracker API should be starting...
    echo 📊 Access at: http://localhost:8000
    echo 🔍 Check logs: docker logs carbontracker-api
    echo 🛑 Stop with: docker stop carbontracker-api
) else (
    echo ❌ Failed to start container!
)

pause