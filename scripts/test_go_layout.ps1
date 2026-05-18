param(
    [string]$Image,
    [string]$OutDir,
    [switch]$Crops,
    [switch]$SkipScan
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$GoExe = Join-Path $Root "local_tools\go\bin\go.exe"
$GoLayout = Join-Path $Root "native\go-layout"
$GoCache = Join-Path $Root ".tmp\go-test-cache"
$GoModCache = Join-Path $Root ".tmp\go-mod-cache"

if (!(Test-Path -LiteralPath $GoExe)) {
    $systemGo = Get-Command go.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($systemGo) {
        $GoExe = $systemGo.Source
    }
    else {
        throw "Go was not found. Run scripts\setup_local_tools.ps1 first to install portable Go."
    }
}

New-Item -ItemType Directory -Force -Path $GoCache, $GoModCache | Out-Null
$env:GOCACHE = $GoCache
$env:GOMODCACHE = $GoModCache

Write-Host "Using Go: $GoExe"
& $GoExe version

Push-Location $GoLayout
try {
    & $GoExe test ./...
    if ($LASTEXITCODE -ne 0) {
        throw "go test failed with exit code $LASTEXITCODE"
    }

    if (!$SkipScan) {
        if (!$Image) {
            $candidate = Join-Path $Root ".tmp\layout_candidate_pages\b.2000-02.037.jpg"
            if (Test-Path -LiteralPath $candidate) {
                $Image = $candidate
            }
            else {
                Write-Host "No default page image found; skipping layoutscan smoke run."
                return
            }
        }
        if (!$OutDir) {
            $OutDir = Join-Path $Root ".tmp\native-layout\smoke"
        }

        New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
        $args = @("run", "./cmd/layoutscan", "--image", $Image, "--out", $OutDir)
        if ($Crops) {
            $args += "--crops"
        }
        & $GoExe @args
        if ($LASTEXITCODE -ne 0) {
            throw "layoutscan smoke run failed with exit code $LASTEXITCODE"
        }
    }
}
finally {
    Pop-Location
}
