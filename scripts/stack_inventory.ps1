param(
    [string]$Base = "origin/review-fixes-2026",
    [string]$Pattern = "codex/stack-*",
    [int]$MaxFiles = 80,
    [switch]$ShowFiles,
    [switch]$Markdown
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

function Get-ShortStat {
    param(
        [string]$From,
        [string]$To
    )

    $ShortStat = (& git -c core.safecrlf=false -c core.quotepath=false diff --shortstat "$From..$To") -join " "
    if ([string]::IsNullOrWhiteSpace($ShortStat)) {
        return "No diff"
    }
    return $ShortStat.Trim()
}

function Get-ChangedFiles {
    param(
        [string]$From,
        [string]$To
    )

    return @(& git -c core.safecrlf=false -c core.quotepath=false diff --name-only "$From..$To")
}

Push-Location $RepoRoot
try {
    $RawRefs = @(& git for-each-ref --format="%(refname:short)|%(objectname:short)|%(subject)" "refs/heads/$Pattern")
    $Stacks = $RawRefs |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        ForEach-Object {
            $Parts = $_ -split "\|", 3
            [PSCustomObject]@{
                Name = $Parts[0]
                Sha = $Parts[1]
                Subject = $Parts[2]
                Number = Get-StackNumber $Parts[0]
            }
        } |
        Sort-Object Number, Name

    if ($Stacks.Count -eq 0) {
        throw "No stack refs matched pattern '$Pattern'."
    }

    $Rows = @()
    $Previous = $Base
    foreach ($Stack in $Stacks) {
        $Files = Get-ChangedFiles $Previous $Stack.Name
        $CommitCount = [int]((& git rev-list --count "$Previous..$($Stack.Name)").Trim())
        $Rows += [PSCustomObject]@{
            Stack = $Stack.Name
            Base = $Previous
            Sha = $Stack.Sha
            Commits = $CommitCount
            Files = $Files.Count
            ShortStat = Get-ShortStat $Previous $Stack.Name
            Subject = $Stack.Subject
            OverLimit = $Files.Count -gt $MaxFiles
            ChangedFiles = $Files
        }
        $Previous = $Stack.Name
    }

    if ($Markdown) {
        Write-Host "| Stack | Base | Commits | Files | Shortstat |"
        Write-Host "| --- | --- | ---: | ---: | --- |"
        foreach ($Row in $Rows) {
            Write-Host ("| `{0}` | `{1}` | {2} | {3} | {4} |" -f $Row.Stack, $Row.Base, $Row.Commits, $Row.Files, $Row.ShortStat)
        }
    }
    else {
        $Rows |
            Select-Object Stack, Base, Commits, Files, ShortStat |
            Format-Table -AutoSize
    }

    $Oversized = @($Rows | Where-Object { $_.OverLimit })
    Write-Host ""
    Write-Host "Base: $Base"
    Write-Host "Stack count: $($Rows.Count)"
    Write-Host "Max files per stack: $MaxFiles"
    if ($Oversized.Count -gt 0) {
        Write-Host "Oversized stacks:"
        foreach ($Row in $Oversized) {
            Write-Host ("- {0}: {1} files" -f $Row.Stack, $Row.Files)
        }
    }
    else {
        Write-Host "Oversized stacks: none"
    }

    if ($ShowFiles) {
        foreach ($Row in $Rows) {
            Write-Host ""
            Write-Host "## $($Row.Stack) files"
            if ($Row.ChangedFiles.Count -eq 0) {
                Write-Host "No files."
            }
            else {
                $Row.ChangedFiles | ForEach-Object { Write-Host $_ }
            }
        }
    }
}
finally {
    Pop-Location
}
