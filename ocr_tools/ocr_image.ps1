param(
    [string]$Url,
    [string]$InputPath,
    [string]$Lang = "rus+eng",
    [int]$Psm = 6,
    [string]$OutDir = "ocr_tools\output"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Tesseract = Join-Path $Root "local_tools\Tesseract-extracted\tesseract.exe"
$TessData = Join-Path $Root "local_tools\Tesseract-extracted\tessdata"
$OutputRoot = Join-Path $Root $OutDir

if (!(Test-Path -LiteralPath $Tesseract)) {
    throw "Tesseract not found at $Tesseract"
}
if (!(Test-Path -LiteralPath $TessData)) {
    throw "Tessdata not found at $TessData"
}
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

if ($Url) {
    $name = [IO.Path]::GetFileName(([Uri]$Url).AbsolutePath)
    if (!$name) { $name = "downloaded_image.png" }
    $safeName = ($name -replace '[^A-Za-z0-9._-]', '_')
    $InputPath = Join-Path $OutputRoot $safeName
    Invoke-WebRequest -Uri $Url -OutFile $InputPath
}

if (!$InputPath) {
    throw "Provide -Url or -InputPath."
}

$ResolvedInput = (Resolve-Path -LiteralPath $InputPath).Path
$base = [IO.Path]::GetFileNameWithoutExtension($ResolvedInput)
$outBase = Join-Path $OutputRoot $base
$txtPath = "$outBase.txt"

& $Tesseract $ResolvedInput $outBase --tessdata-dir $TessData -l $Lang --psm $Psm

[pscustomobject]@{
    Input = $ResolvedInput
    TextFile = (Resolve-Path -LiteralPath $txtPath).Path
    Language = $Lang
    Psm = $Psm
    Text = (Get-Content -LiteralPath $txtPath -Raw -Encoding UTF8)
}
