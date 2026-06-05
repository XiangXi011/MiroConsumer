param(
    [string]$Base = "review-fixes-2026",
    [string]$Pattern = "codex/stack-*",
    [string]$RepositoryUrl = "https://github.com/XiangXi011/MiroConsumer",
    [switch]$Plain
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot

function Get-StackNumber {
    param([string]$Name)

    if ($Name -match "stack-(\d+)") {
        return [int]$Matches[1]
    }
    return [int]::MaxValue
}

Push-Location $RepoRoot
try {
    $Branches = @(
        & git branch --list $Pattern --format="%(refname:short)" |
            Sort-Object { Get-StackNumber $_ }, { $_ }
    )

    if ($Branches.Count -eq 0) {
        throw "No stack branches matched pattern '$Pattern'."
    }

    $Previous = $Base
    if (-not $Plain) {
        Write-Host "| Stack | Base | Head | Compare link |"
        Write-Host "| --- | --- | --- | --- |"
    }

    foreach ($Branch in $Branches) {
        $CompareUrl = "$RepositoryUrl/compare/${Previous}...${Branch}?expand=1"

        if ($Plain) {
            Write-Host "$Branch"
            Write-Host "  Base: $Previous"
            Write-Host "  Head: $Branch"
            Write-Host "  Compare: $CompareUrl"
        }
        else {
            Write-Host ("| `{0}` | `{1}` | `{2}` | [open]({3}) |" -f $Branch, $Previous, $Branch, $CompareUrl)
        }

        $Previous = $Branch
    }
}
finally {
    Pop-Location
}
