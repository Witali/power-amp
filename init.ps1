param(
    [switch]$Force,
    [switch]$SkipNgspice,
    [switch]$SkipOcr,
    [switch]$SkipSpellcheck,
    [switch]$InstallHunspell,
    [switch]$SkipNode,
    [string]$SevenZipPath
)

$ErrorActionPreference = "Stop"
$Script = Join-Path $PSScriptRoot "scripts\setup_local_tools.ps1"

& $Script -Force:$Force -SkipNgspice:$SkipNgspice -SkipOcr:$SkipOcr -SkipSpellcheck:$SkipSpellcheck -InstallHunspell:$InstallHunspell -SkipNode:$SkipNode -SevenZipPath $SevenZipPath
