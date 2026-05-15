$ErrorActionPreference = "Stop"

$Skill = $null
$AutoOverwrite = $false

function Show-Usage {
  Write-Host "Usage:"
  Write-Host "  .\install-copilot-skills.ps1 [--y]"
  Write-Host "  .\install-copilot-skills.ps1 -Skill <skill-name> [--y]"
  Write-Host ""
  Write-Host "Installs skill folders into `$HOME\.copilot\skills."
  Write-Host "Use --y to overwrite existing installed skills without prompting."
}

function Read-Arguments {
  for ($index = 0; $index -lt $args.Count; $index++) {
    $arg = [string]$args[$index]
    switch ($arg) {
      "-Skill" {
        if (($index + 1) -ge $args.Count -or [string]::IsNullOrWhiteSpace([string]$args[$index + 1])) {
          Show-Usage
          exit 1
        }
        $script:Skill = [string]$args[$index + 1]
        $index += 1
      }
      "--skill" {
        if (($index + 1) -ge $args.Count -or [string]::IsNullOrWhiteSpace([string]$args[$index + 1])) {
          Show-Usage
          exit 1
        }
        $script:Skill = [string]$args[$index + 1]
        $index += 1
      }
      "--y" {
        $script:AutoOverwrite = $true
      }
      "-Y" {
        $script:AutoOverwrite = $true
      }
      "-y" {
        $script:AutoOverwrite = $true
      }
      "-h" {
        Show-Usage
        exit 0
      }
      "--help" {
        Show-Usage
        exit 0
      }
      default {
        Write-Host "Unsupported option: $arg"
        Show-Usage
        exit 1
      }
    }
  }
}

function Ask-YesNo {
  param([string]$Prompt)
  $answer = Read-Host "$Prompt [y/N]"
  return $answer -match '^(y|yes)$'
}

function Invoke-Git {
  param([string[]]$Arguments)
  $output = & git -C $ScriptRoot @Arguments 2>$null
  if ($LASTEXITCODE -ne 0) {
    return $null
  }
  return ($output -join "`n").Trim()
}

function Check-LatestVersion {
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Note: git is not available, so automatic latest-version checking is unavailable."
    return
  }

  $inside = Invoke-Git @("rev-parse", "--is-inside-work-tree")
  if ($inside -ne "true") {
    Write-Host "Note: automatic latest-version checking is unavailable because this folder is not a Git repository."
    return
  }

  $upstream = Invoke-Git @("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
  if ([string]::IsNullOrWhiteSpace($upstream)) {
    Write-Host "Note: automatic latest-version checking is unavailable because no upstream remote is configured."
    return
  }

  & git -C $ScriptRoot fetch --quiet
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: failed to fetch remote metadata. Continuing with the current local version."
    return
  }

  $localHead = Invoke-Git @("rev-parse", "HEAD")
  $upstreamHead = Invoke-Git @("rev-parse", $upstream)
  $mergeBase = Invoke-Git @("merge-base", "HEAD", $upstream)

  if ($localHead -eq $upstreamHead) {
    Write-Host "Local skills are up to date."
  } elseif ($mergeBase -eq $localHead) {
    if (Ask-YesNo "Local skills are not the latest version. Update before installing?") {
      & git -C $ScriptRoot pull --ff-only
      if ($LASTEXITCODE -ne 0) {
        throw "git pull --ff-only failed. Stop installing."
      }
    } else {
      Write-Host "Continuing with the current local version."
    }
  } else {
    Write-Host "Warning: local skills differ from upstream. Continuing with the current local version."
  }
}

function Test-SkillFolder {
  param([string]$Path)
  return (Test-Path -LiteralPath $Path -PathType Container) -and (Test-Path -LiteralPath (Join-Path $Path "SKILL.md") -PathType Leaf)
}

function Copy-SkillFolder {
  param(
    [string]$Source,
    [string]$Destination
  )

  New-Item -ItemType Directory -Path $Destination -Force | Out-Null
  $sourceRoot = (Resolve-Path -LiteralPath $Source).Path

  Get-ChildItem -LiteralPath $Source -Recurse -Force |
    Where-Object {
      $_.Name -ne ".DS_Store" -and
      ($_.FullName -split [regex]::Escape([IO.Path]::DirectorySeparatorChar)) -notcontains "node_modules"
    } |
    ForEach-Object {
      $relative = $_.FullName.Substring($sourceRoot.Length).TrimStart([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
      if ([string]::IsNullOrWhiteSpace($relative)) {
        return
      }
      $targetPath = Join-Path $Destination $relative
      if ($_.PSIsContainer) {
        New-Item -ItemType Directory -Path $targetPath -Force | Out-Null
      } else {
        $parent = Split-Path -Parent $targetPath
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $targetPath -Force
      }
    }
}

function Install-Skill {
  param([string]$Name)

  $source = Join-Path $ScriptRoot $Name
  $destination = Join-Path $TargetDir $Name

  if (-not (Test-SkillFolder $source)) {
    throw "requested skill `"$Name`" does not exist or lacks SKILL.md."
  }

  if (Test-Path -LiteralPath $destination) {
    if ($AutoOverwrite -or (Ask-YesNo "Skill `"$Name`" already exists in target. Overwrite?")) {
      $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
      $backupDir = Join-Path $TargetDir ".backup"
      $backupPath = Join-Path $backupDir "$Name-$timestamp"
      New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
      if (Test-Path -LiteralPath $backupPath) {
        $backupPath = "$backupPath-$PID"
      }
      Move-Item -LiteralPath $destination -Destination $backupPath
      Write-Host "Backed up existing `"$Name`" to $backupPath"
    } else {
      Write-Host "Skipped `"$Name`"."
      return
    }
  }

  Copy-SkillFolder -Source $source -Destination $destination
  Write-Host "Installed `"$Name`" to $destination"
}

Read-Arguments @args

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$TargetDir = Join-Path $HOME ".copilot\skills"

Check-LatestVersion
New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

if (-not [string]::IsNullOrWhiteSpace($Skill)) {
  Install-Skill -Name $Skill
} else {
  $skills = Get-ChildItem -LiteralPath $ScriptRoot -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "SKILL.md") } |
    Sort-Object Name

  if ($skills.Count -eq 0) {
    throw "no skill folders containing SKILL.md were found."
  }

  foreach ($skillFolder in $skills) {
    Install-Skill -Name $skillFolder.Name
  }
}
