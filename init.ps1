param(
    [switch]$Force,
    [switch]$SkipNgspice,
    [switch]$SkipOcr,
    [switch]$SkipSpellcheck,
    [switch]$InstallHunspell,
    [switch]$SkipLayoutCv,
    [switch]$SkipGo,
    [switch]$SkipNode,
    [string]$SevenZipPath
)

$ErrorActionPreference = "Stop"
$Script = Join-Path $PSScriptRoot "scripts\setup_local_tools.ps1"

& $Script -Force:$Force -SkipNgspice:$SkipNgspice -SkipOcr:$SkipOcr -SkipSpellcheck:$SkipSpellcheck -InstallHunspell:$InstallHunspell -SkipLayoutCv:$SkipLayoutCv -SkipGo:$SkipGo -SkipNode:$SkipNode -SevenZipPath $SevenZipPath
