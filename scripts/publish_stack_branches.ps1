param(
    [string]$Remote = "origin",
    [string]$Pattern = "codex/stack-*",
    [int]$StartAt = 1,
    [int]$EndAt = [int]::MaxValue,
    [int]$BatchSize = 3,
    [switch]$Push
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

if ($BatchSize -lt 1) {
    throw "BatchSize must be at least 1."
}

Push-Location $RepoRoot
try {
    $Branches = @(
        & git branch --list $Pattern --format="%(refname:short)" |
            Where-Object {
                $Number = Get-StackNumber $_
                $Number -ge $StartAt -and $Number -le $EndAt
            } |
            Sort-Object { Get-StackNumber $_ }, { $_ }
    )

    if ($Branches.Count -eq 0) {
        throw "No stack branches matched pattern '$Pattern' in range $StartAt..$EndAt."
    }

    if ($Push) {
        Write-Host "Publishing $($Branches.Count) stack branch(es) to $Remote in batches of $BatchSize."
    }
    else {
        Write-Host "Dry-run: $($Branches.Count) stack branch(es) would be published to $Remote in batches of $BatchSize."
        Write-Host "Pass -Push to publish."
    }

    for ($Index = 0; $Index -lt $Branches.Count; $Index += $BatchSize) {
        $Batch = @($Branches[$Index..([Math]::Min($Index + $BatchSize - 1, $Branches.Count - 1))])
        Write-Host ""
        Write-Host ("Batch {0}-{1}:" -f ($Index + 1), ($Index + $Batch.Count))
        $Batch | ForEach-Object { Write-Host "  $_" }

        if ($Push) {
            & git push $Remote $Batch
        }
    }
}
finally {
    Pop-Location
}
