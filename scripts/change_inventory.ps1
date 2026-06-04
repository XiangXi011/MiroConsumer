param(
    [string]$Base = "origin/review-fixes-2026",
    [switch]$ShowFiles
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot

function Get-Area {
    param([string]$Path)

    $Normalized = $Path -replace "\\", "/"
    switch -Regex ($Normalized) {
        "^\.github/" { return ".github" }
        "^backend/app/" { return "backend/app" }
        "^backend/tests/" { return "backend/tests" }
        "^backend/" { return "backend/other" }
        "^frontend/src/" { return "frontend/src" }
        "^frontend/tests/" { return "frontend/tests" }
        "^frontend/" { return "frontend/other" }
        "^docs/" { return "docs" }
        "^locales/" { return "locales" }
        "^scripts/" { return "scripts" }
        default { return ($Normalized -split "/")[0] }
    }
}

function Write-Section {
    param([string]$Title)

    Write-Host ""
    Write-Host "## $Title"
}

function Write-PathGroups {
    param(
        [string]$Title,
        [string[]]$Paths
    )

    Write-Section $Title
    if ($Paths.Count -eq 0) {
        Write-Host "No files."
        return
    }

    $Groups = $Paths |
        ForEach-Object { Get-Area $_ } |
        Group-Object |
        Sort-Object @{ Expression = "Count"; Descending = $true }, @{ Expression = "Name"; Descending = $false }

    foreach ($Group in $Groups) {
        Write-Host ("{0,5}  {1}" -f $Group.Count, $Group.Name)
    }
}

Push-Location $RepoRoot
try {
    $Branch = (& git branch --show-current).Trim()
    $Upstream = & git rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>$null
    if ($LASTEXITCODE -ne 0) {
        $Upstream = "(none)"
    }

    $AheadBehind = & git rev-list --left-right --count "$Base...HEAD"
    $BaseShortStat = (& git -c core.safecrlf=false -c core.quotepath=false diff --shortstat "$Base...HEAD") -join ""
    if ([string]::IsNullOrWhiteSpace($BaseShortStat)) {
        $BaseShortStat = "No committed diff against $Base."
    }

    $WorktreeShortStat = (& git -c core.safecrlf=false -c core.quotepath=false diff --shortstat) -join ""
    if ([string]::IsNullOrWhiteSpace($WorktreeShortStat)) {
        $WorktreeShortStat = "No tracked worktree diff."
    }

    $CommittedFiles = @(& git -c core.safecrlf=false -c core.quotepath=false diff --name-only "$Base...HEAD")
    $WorktreeFiles = @(& git -c core.safecrlf=false -c core.quotepath=false diff --name-only)
    $UntrackedFiles = @(& git -c core.quotepath=false ls-files --others --exclude-standard)
    $LocalFiles = @($WorktreeFiles + $UntrackedFiles) | Sort-Object -Unique

    Write-Host "Branch: $Branch"
    Write-Host "Upstream: $Upstream"
    Write-Host "Base: $Base"
    Write-Host "Base...HEAD commits (left/right): $AheadBehind"

    Write-Section "Committed Diff Against Base"
    Write-Host $BaseShortStat
    Write-Host "Changed files: $($CommittedFiles.Count)"

    Write-Section "Local Worktree Diff"
    Write-Host $WorktreeShortStat
    Write-Host "Tracked changed files: $($WorktreeFiles.Count)"
    Write-Host "Untracked files: $($UntrackedFiles.Count)"
    Write-Host "Total local changed/untracked files: $($LocalFiles.Count)"

    Write-PathGroups "Committed Diff By Area" $CommittedFiles
    Write-PathGroups "Local Worktree By Area" $LocalFiles

    if ($ShowFiles) {
        Write-Section "Local Changed/Untracked Files"
        $LocalFiles | ForEach-Object { Write-Host $_ }
    }

    Write-Section "Risk Hints"
    if ($LocalFiles.Count -gt 100) {
        Write-Host "- Local change count is above 100 files; split before PR review."
    }
    if ($CommittedFiles.Count -gt 80) {
        Write-Host "- Committed diff against base is above 80 files; prefer stacked PRs."
    }
    if ($UntrackedFiles.Count -gt 0) {
        Write-Host "- Untracked files remain; decide whether each belongs in this repo."
    }
}
finally {
    Pop-Location
}
