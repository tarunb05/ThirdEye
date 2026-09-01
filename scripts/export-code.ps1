param(
  [string]$Root = ".",
  [string]$Output = "thirdeye-code-export.txt"
)

# Code-only extensions
$includeExtensions = @(
  ".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".html"
)

# Skip heavy / irrelevant dirs
$excludeDirs = @(
  "node_modules",
  ".git",
  ".venv",
  "venv",
  "__pycache__",
  "dist",
  "build",
  ".next",
  ".idea",
  ".vscode"
)

Write-Host "Exporting CODE from '$Root' to '$Output'..." -ForegroundColor Cyan
"" | Out-File -FilePath $Output -Encoding UTF8

Get-ChildItem -Path $Root -Recurse -File | ForEach-Object {
  $file = $_

  # Skip excluded dirs
  foreach ($ex in $excludeDirs) {
    if ($file.FullName -like "*\$ex\*") { return }
  }

  # Only include whitelisted code extensions
  if (-not ($includeExtensions -contains $file.Extension.ToLower())) { return }

  # Compute relative path for nicer tree
  $relPath = Resolve-Path $file.FullName | ForEach-Object {
    $_.Path.Replace((Resolve-Path $Root).Path, ".")
  }

@"
================================================================
PATH: $relPath
================================================================

"@ | Out-File -FilePath $Output -Append -Encoding UTF8

  try {
    Get-Content -Path $file.FullName -Raw -ErrorAction Stop |
      Out-File -FilePath $Output -Append -Encoding UTF8
  } catch {
    "<<< Could not read this file as text >>>`n" |
      Out-File -FilePath $Output -Append -Encoding UTF8
  }

  "`n`n" | Out-File -FilePath $Output -Append -Encoding UTF8
}

Write-Host "Done. Export written to '$Output'." -ForegroundColor Green