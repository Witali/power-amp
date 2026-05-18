param(
    [switch]$SkipTests,
    [switch]$SkipBuild,
    [switch]$Smoke,
    [switch]$Crops,
    [switch]$UseSystemGo,
    [string]$Image,
    [string]$OutDir,
    [string]$BinDir,
    [int]$MaxSide = 1800
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$LocalGoRoot = Join-Path $Root "local_tools\go"
$LocalGoExe = Join-Path $LocalGoRoot "bin\go.exe"
$GoCache = Join-Path $Root ".tmp\go-build-cache"
$GoModCache = Join-Path $Root ".tmp\go-mod-cache"

if (!$BinDir) {
    $BinDir = Join-Path $Root "local_tools\bin"
}

function Resolve-GoExe {
    if (!$UseSystemGo -and (Test-Path -LiteralPath $LocalGoExe)) {
        $env:GOROOT = $LocalGoRoot
        return $LocalGoExe
    }

    $systemGo = Get-Command go.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($systemGo) {
        return $systemGo.Source
    }

    throw "Go was not found. Run scripts\setup_local_tools.ps1 to install portable Go."
}

function Get-GoCommandPackages {
    $nativeRoot = Join-Path $Root "native"
    if (!(Test-Path -LiteralPath $nativeRoot)) {
        return @()
    }

    $items = @()
    $modules = Get-ChildItem -LiteralPath $nativeRoot -Recurse -Filter "go.mod" -File
    foreach ($module in $modules) {
        $moduleDir = $module.Directory.FullName
        $cmdRoot = Join-Path $moduleDir "cmd"
        if (!(Test-Path -LiteralPath $cmdRoot)) {
            continue
        }
        foreach ($commandDir in Get-ChildItem -LiteralPath $cmdRoot -Directory) {
            $items += [pscustomobject]@{
                ModuleDir = $moduleDir
                Name      = $commandDir.Name
                Package   = "./cmd/$($commandDir.Name)"
                Output    = Join-Path $BinDir "$($commandDir.Name).exe"
            }
        }
    }
    return $items
}

New-Item -ItemType Directory -Force -Path $GoCache, $GoModCache, $BinDir | Out-Null
$env:GOCACHE = $GoCache
$env:GOMODCACHE = $GoModCache

$GoExe = Resolve-GoExe
$env:PATH = "$(Split-Path -Parent $GoExe);$env:PATH"

Write-Host "Using Go: $GoExe"
& $GoExe version
Write-Host "GOCACHE:   $env:GOCACHE"
Write-Host "GOMODCACHE:$env:GOMODCACHE"
Write-Host "BinDir:    $BinDir"

$commands = @(Get-GoCommandPackages)
if ($commands.Count -eq 0) {
    Write-Host "No Go command packages found under native/*/cmd/*."
    exit 0
}

$moduleDirs = @($commands | Select-Object -ExpandProperty ModuleDir -Unique)
foreach ($moduleDir in $moduleDirs) {
    Push-Location $moduleDir
    try {
        if (!$SkipTests) {
            Write-Host ""
            Write-Host "==> go test ./... in $moduleDir"
            & $GoExe test ./...
            if ($LASTEXITCODE -ne 0) {
                throw "go test failed in $moduleDir with exit code $LASTEXITCODE"
            }
        }

        if (!$SkipBuild) {
            foreach ($command in $commands | Where-Object { $_.ModuleDir -eq $moduleDir }) {
                Write-Host ""
                Write-Host "==> go build $($command.Package) -> $($command.Output)"
                & $GoExe build -trimpath -ldflags "-s -w" -o $command.Output $command.Package
                if ($LASTEXITCODE -ne 0) {
                    throw "go build failed for $($command.Package) with exit code $LASTEXITCODE"
                }
            }
        }
    }
    finally {
        Pop-Location
    }
}

if ($Smoke) {
    $layoutscan = Join-Path $BinDir "layoutscan.exe"
    if (!(Test-Path -LiteralPath $layoutscan)) {
        throw "layoutscan.exe was not built: $layoutscan"
    }

    if (!$Image) {
        $candidate = Join-Path $Root ".tmp\layout_candidate_pages\b.2000-02.037.jpg"
        if (Test-Path -LiteralPath $candidate) {
            $Image = $candidate
        }
        else {
            Write-Host "No default page image found; skipping smoke run."
            exit 0
        }
    }
    if (!$OutDir) {
        $OutDir = Join-Path $Root ".tmp\native-layout\compiled-smoke"
    }

    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
    $args = @("--image", $Image, "--out", $OutDir, "--max-side", "$MaxSide")
    if ($Crops) {
        $args += "--crops"
    }

    Write-Host ""
    Write-Host "==> layoutscan smoke run"
    & $layoutscan @args
    if ($LASTEXITCODE -ne 0) {
        throw "layoutscan smoke run failed with exit code $LASTEXITCODE"
    }
}
