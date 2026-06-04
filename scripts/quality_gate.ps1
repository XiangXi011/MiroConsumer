param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$BackendSmoke
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"

function Invoke-Step {
    param(
        [string]$Name,
        [string]$WorkingDirectory,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "==> $Name"
    Push-Location $WorkingDirectory
    try {
        & $Command
    }
    finally {
        Pop-Location
    }
}

if (-not $FrontendOnly) {
    Invoke-Step "Backend Ruff" $BackendDir {
        uv run --python 3.12 ruff check app tests
    }

    if ($BackendSmoke) {
        Invoke-Step "Backend OpenClaw and research smoke tests" $BackendDir {
            uv run --python 3.12 pytest `
                tests\consumer\test_research_ingest.py `
                tests\api\test_openclaw_routes.py `
                tests\services\application\test_openclaw_orchestrator.py `
                -v --tb=short --no-cov
        }
    }
}

if (-not $BackendOnly) {
    Invoke-Step "Frontend dependencies" $FrontendDir {
        if (-not (Test-Path "node_modules")) {
            npm ci
        }
    }

    Invoke-Step "Frontend typecheck" $FrontendDir {
        npm run typecheck
    }

    Invoke-Step "Frontend Vitest" $FrontendDir {
        npx vitest run
    }
}
