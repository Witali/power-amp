param(
    [Parameter(Mandatory = $true)]
    [string]$Netlist,

    [string]$OutputDir
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Ngspice = Join-Path $Root "local_tools\ngspice\Spice64\bin\ngspice_con.exe"

if (!(Test-Path -LiteralPath $Ngspice)) {
    throw "ngspice not found at $Ngspice"
}

$NetlistPath = (Resolve-Path -LiteralPath $Netlist).Path
if (!$OutputDir) {
    $OutputDir = Split-Path -Parent $NetlistPath
}
$OutputFull = [IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputDir))
New-Item -ItemType Directory -Force -Path $OutputFull | Out-Null

$LogPath = Join-Path $OutputFull "ngspice.log"

Push-Location $OutputFull
try {
    & $Ngspice -b -o $LogPath $NetlistPath
    $exit = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($exit -ne 0) {
    throw "ngspice failed with exit code $exit. See $LogPath"
}

[pscustomobject]@{
    Ngspice = $Ngspice
    Netlist = $NetlistPath
    OutputDir = $OutputFull
    Log = $LogPath
}
