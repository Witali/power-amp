param(
    [switch]$Force,
    [switch]$SkipNgspice,
    [switch]$SkipOcr,
    [switch]$SkipNode,
    [string]$SevenZipPath
)

$ErrorActionPreference = "Stop"
$Script = Join-Path $PSScriptRoot "scripts\setup_local_tools.ps1"

& $Script -Force:$Force -SkipNgspice:$SkipNgspice -SkipOcr:$SkipOcr -SkipNode:$SkipNode -SevenZipPath $SevenZipPath
