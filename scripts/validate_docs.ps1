# Documentation validation helper
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$failures = @()

$markdown = Get-ChildItem -Path $root -Recurse -File -Filter *.md |
  Where-Object { $_.FullName -notmatch "\\node_modules\\|\\\.venv\\|\\output\\|\\test-results\\" }

foreach ($file in $markdown) {
  $text = Get-Content -Raw -LiteralPath $file.FullName
  if ($text -match "(?i)(AKIA[0-9A-Z]{16}|-----BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY-----|sk-[A-Za-z0-9_-]{16,})") {
    $failures += "Possible credential pattern in $($file.FullName)"
  }
  $links = [regex]::Matches($text, "\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)")
  foreach ($link in $links) {
    $target = $link.Groups[1].Value
    if ($target -match "^(https?://|mailto:|#)") { continue }
    $resolved = Join-Path $file.DirectoryName $target
    if (-not (Test-Path -LiteralPath $resolved)) {
      $failures += "Missing relative link in $($file.FullName): $target"
    }
  }
}

$mermaid = Get-ChildItem -Path (Join-Path $root "docs/diagrams") -File -Filter *.mmd
foreach ($file in $mermaid) {
  $text = Get-Content -Raw -LiteralPath $file.FullName
  if ($text -notmatch "(?m)^(flowchart|graph|sequenceDiagram)\b") {
    $failures += "Mermaid source has no recognized diagram declaration: $($file.FullName)"
  }
}

$tracked = git -C $root ls-files
foreach ($path in $tracked) {
  $approvedTemplate = $path -in @("backend/.env.example", "frontend/.env.example", "frontend/.env.production")
  if (-not $approvedTemplate -and $path -match "(^|/)\.env$|(^|/)\.env\.(?!example$)|(^|/).*\.pem$|(^|/).*\.key$") {
    $failures += "Tracked secret-like path: $path"
  }
}

if ($failures.Count -gt 0) {
  $failures | ForEach-Object { Write-Error $_ }
  exit 1
}

Write-Output ("Documentation validation passed: {0} Markdown files and {1} Mermaid sources checked." -f $markdown.Count, $mermaid.Count)
