function Get-GitHubAnchor([string]$heading) {
  $value = $heading.ToLowerInvariant()
  $value = [regex]::Replace($value, "<[^>]+>", "")
  $value = $value.Replace(([char]96).ToString(), "")
  $value = $value -replace "[^a-z0-9 -]", ""
  $value = $value -replace "\s+", "-"
  $value = $value -replace "-+", "-"
  return $value.Trim("-")
}
