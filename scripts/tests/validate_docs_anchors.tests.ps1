$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\docs_validation_helpers.ps1")

function Assert-Equal([string]$expected, [string]$actual, [string]$name) {
  if ($expected -cne $actual) {
    throw "$name failed: expected '$expected', got '$actual'"
  }
}

Assert-Equal "hello-world" (Get-GitHubAnchor "Hello, world!") "punctuation slug"
Assert-Equal "multi-word-heading" (Get-GitHubAnchor "Multi   word heading") "whitespace slug"
Assert-Equal "heading-with-code" (Get-GitHubAnchor 'Heading with `code`') "inline code slug"

$counts = @{}
$duplicateSlugs = foreach ($heading in @("Duplicate heading", "Duplicate heading")) {
  $slug = Get-GitHubAnchor $heading
  if ($counts.ContainsKey($slug)) {
    $counts[$slug]++
    "$slug-$($counts[$slug])"
  } else {
    $counts[$slug] = 0
    $slug
  }
}
Assert-Equal "duplicate-heading" $duplicateSlugs[0] "first duplicate heading"
Assert-Equal "duplicate-heading-1" $duplicateSlugs[1] "second duplicate heading"

$fixture = @(
  "# Valid Heading",
  "",
  "[valid](./fixture.md#valid-heading)",
  "[invalid](./fixture.md#missing-heading)"
)
$fixturePath = Join-Path $PSScriptRoot "fixture.md"
try {
  Set-Content -LiteralPath $fixturePath -Value $fixture -Encoding utf8
  $fixtureText = Get-Content -Raw -LiteralPath $fixturePath
  $headingMatch = [regex]::Match($fixtureText, "(?m)^#{1,6}\s+(.+?)\s*#*\s*$")
  $fixtureAnchor = Get-GitHubAnchor $headingMatch.Groups[1].Value
  $validTarget = "fixture.md#$fixtureAnchor"
  $invalidTarget = "fixture.md#missing-heading"
  Assert-Equal "True" ([string]($validTarget -eq "fixture.md#valid-heading")) "valid relative anchor"
  Assert-Equal "False" ([string]($invalidTarget -eq "fixture.md#$fixtureAnchor")) "invalid relative anchor"
} finally {
  if (Test-Path -LiteralPath $fixturePath) {
    Remove-Item -LiteralPath $fixturePath -Force
  }
}

Write-Output "Focused documentation anchor tests passed: slugs, punctuation, duplicates, valid/invalid relative anchors."
