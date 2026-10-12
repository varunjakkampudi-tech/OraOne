# Documentation validation helper
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$failures = [System.Collections.Generic.List[string]]::new()
$fence = [char]96 + [char]96 + [char]96
. (Join-Path $PSScriptRoot "docs_validation_helpers.ps1")

function Add-Failure([string]$message) {
  [void]$failures.Add($message)
}

$markdown = @(Get-ChildItem -Path $root -Recurse -File -Filter *.md |
  Where-Object {
    $_.FullName -notmatch "\\node_modules\\|\\.venv\\|\\build\\|\\output\\|\\test-results\\"
  })

$anchors = @{}
foreach ($file in $markdown) {
  $counts = @{}
  $lines = Get-Content -LiteralPath $file.FullName
  $insideFence = $false
  $fenceKind = ""
  foreach ($line in $lines) {
    if ($line -match ("^\s*(" + [regex]::Escape($fence) + "|~~~)")) {
      $kind = $Matches[1]
      if (-not $insideFence) {
        $insideFence = $true
        $fenceKind = $kind
      } elseif ($kind -eq $fenceKind) {
        $insideFence = $false
        $fenceKind = ""
      }
      continue
    }
    if (-not $insideFence -and $line -match "^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$") {
      $slug = Get-GitHubAnchor $Matches[1]
      if ($counts.ContainsKey($slug)) {
        $counts[$slug]++
        $slug = "$slug-$($counts[$slug])"
      } else {
        $counts[$slug] = 0
      }
      $anchors["$($file.FullName)|$slug"] = $true
    }
  }
  if ($insideFence) {
    Add-Failure "Unclosed Markdown fence in $($file.FullName)"
  }

  $text = Get-Content -Raw -LiteralPath $file.FullName
  if ($text -match "(?i)(AKIA[0-9A-Z]{16}|-----BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY-----|sk-[A-Za-z0-9_-]{16,})") {
    Add-Failure "Possible credential pattern in $($file.FullName)"
  }
  if ($text -match "\]\([^)]*$") {
    Add-Failure "Malformed Markdown link in $($file.FullName)"
  }

  $links = [regex]::Matches($text, "\[[^\]]+\]\(([^)]+)\)")
  foreach ($link in $links) {
    $target = $link.Groups[1].Value.Trim()
    if ($target -match "^(https?://|mailto:|data:)") { continue }
    $parts = $target.Split("#", 2)
    $relative = $parts[0]
    $fragment = if ($parts.Count -eq 2) { $parts[1] } else { $null }
    $resolved = if ([string]::IsNullOrWhiteSpace($relative)) {
      $file.FullName
    } else {
      Join-Path $file.DirectoryName $relative
    }
    if (-not (Test-Path -LiteralPath $resolved)) {
      Add-Failure "Missing relative link in $($file.FullName): $target"
      continue
    }
    if ($fragment) {
      $resolvedFull = (Resolve-Path -LiteralPath $resolved).Path
      $slug = Get-GitHubAnchor $fragment
      if (-not $anchors.ContainsKey("$resolvedFull|$slug")) {
        Add-Failure "Missing Markdown anchor in $($file.FullName): $target"
      }
    }
  }
}

$mermaidDir = Join-Path $root "docs/diagrams"
$mermaid = @(Get-ChildItem -Path $mermaidDir -File -Filter *.mmd)
if ($mermaid.Count -ne 10) {
  Add-Failure "Expected 10 Mermaid source diagrams, found $($mermaid.Count)"
}

$sourceByPath = @{}
foreach ($file in $mermaid) {
  $source = (Get-Content -Raw -LiteralPath $file.FullName).Trim()
  $sourceByPath["docs/diagrams/$($file.Name)"] = $source
  $lines = $source -split "\r?\n"
  if ($lines[0] -notmatch "^(flowchart|graph|sequenceDiagram)\b") {
    Add-Failure "Mermaid source has no recognized diagram type: $($file.FullName)"
  }
  if (($source -match "\[") -ne ($source -match "\]")) {
    Add-Failure "Unbalanced square-bracket syntax in $($file.FullName)"
  }
  if (($source -match "\(") -ne ($source -match "\)")) {
    Add-Failure "Unbalanced parenthesis syntax in $($file.FullName)"
  }
  if ($lines[0] -match "^(flowchart|graph)" -and $source -notmatch "-->|-.+->|==>") {
    Add-Failure "Flowchart has no edge syntax: $($file.FullName)"
  }
  if ($lines[0] -eq "sequenceDiagram" -and ($source -notmatch "(?m)^\s*participant\s" -or $source -notmatch "->>")) {
    Add-Failure "Sequence diagram lacks participants or message arrows: $($file.FullName)"
  }
}

$embedded = @{}
$mermaidFence = [regex]::Escape($fence)
foreach ($file in $markdown) {
  $text = Get-Content -Raw -LiteralPath $file.FullName
  $matches = [regex]::Matches($text, "<!-- diagram: (docs/diagrams/[^ ]+\.mmd) -->\s*"+$mermaidFence+"mermaid\s*([\s\S]*?)"+$mermaidFence)
  foreach ($match in $matches) {
    $path = $match.Groups[1].Value
    $embedded[$path] = $true
    if (-not $sourceByPath.ContainsKey($path)) {
      Add-Failure "Embedded Mermaid source does not exist: $path in $($file.FullName)"
    } elseif ($sourceByPath[$path] -ne $match.Groups[2].Value.Trim()) {
      Add-Failure "Embedded Mermaid drift from source: $path in $($file.FullName)"
    }
  }
}
foreach ($path in $sourceByPath.Keys) {
  if (-not $embedded.ContainsKey($path)) {
    Add-Failure "Mermaid source is not embedded in Markdown: $path"
  }
}

$tracked = & git -C $root ls-files 2>&1
if ($LASTEXITCODE -ne 0) {
  Add-Failure "git ls-files failed with exit code $LASTEXITCODE"
}
foreach ($path in $tracked) {
  $approvedTemplate = $path -eq "frontend/.env.production"
  if (-not $approvedTemplate -and $path -match "(^|/)\.env$|(^|/)\.env\.(?!example$)|(^|/).*\.pem$|(^|/).*\.key$") {
    Add-Failure "Tracked secret-like path: $path"
  }
}

if ($failures.Count -gt 0) {
  $failures | ForEach-Object { Write-Error $_ }
  exit 1
}

Write-Output ("Documentation validation passed: {0} Markdown files, {1} Mermaid sources, {2} embedded diagrams checked." -f $markdown.Count, $mermaid.Count, $embedded.Count)
