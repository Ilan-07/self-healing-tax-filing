Set-Location "$PSScriptRoot\..\backend"
py -m uvicorn app.main:app --reload --port 8000
