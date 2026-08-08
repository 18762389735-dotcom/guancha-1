$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$requiredPaths = @(
    'backend/.gitkeep',
    'supabase/migrations/.gitkeep',
    'test-fixtures/.gitkeep',
    'index.html',
    'app.js',
    'docs/FRONTEND_AUDIT.md',
    'docs/BACKEND_GAP_ANALYSIS.md',
    'docs/API_MAPPING.md'
)

foreach ($relativePath in $requiredPaths) {
    if (-not (Test-Path (Join-Path $root $relativePath))) {
        throw "Required baseline path is missing: $relativePath"
    }
}

$node = Get-Command node -ErrorAction SilentlyContinue
if ($null -eq $node) {
    throw 'Node.js is required to check app.js syntax.'
}

& $node.Source --check (Join-Path $root 'app.js')
if ($LASTEXITCODE -ne 0) {
    throw 'Frontend JavaScript syntax check failed.'
}

$forbiddenTrackedPatterns = @(
    '(^|/)\.env($|\.)',
    '(^|/)node_modules/',
    '(^|/)uploads/',
    '(^|/)user-images/',
    '(^|/)playwright-report/',
    '(^|/)test-results/',
    '(^|/)__pycache__/'
)
$trackedFiles = & git -C $root -c core.quotepath=false ls-files
foreach ($pattern in $forbiddenTrackedPatterns) {
    if ($trackedFiles | Select-String -Pattern $pattern -Quiet) {
        throw "Forbidden tracked path matched: $pattern"
    }
}

$secretPattern = '(-----BEGIN (RSA|EC|OPENSSH|DSA|PGP) PRIVATE KEY-----|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})'
$scanFiles = $trackedFiles | Where-Object {
    $_ -notmatch '^(assets|uploads|user-images)/' -and $_ -notmatch '\.(png|jpe?g|webp|gif|svg|ico|pdf)$'
}
if ($scanFiles.Count -gt 0) {
    $matches = $scanFiles | ForEach-Object {
        $candidate = Join-Path $root $_
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            Select-String -LiteralPath $candidate -Pattern $secretPattern -AllMatches -List -ErrorAction Stop
        }
    }
    if ($matches) {
        throw 'Potential secret pattern detected in tracked text files.'
    }
}

Write-Host 'Baseline verification passed.'
