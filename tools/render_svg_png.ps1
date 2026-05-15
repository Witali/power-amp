param(
    [Parameter(Mandatory = $true)]
    [string]$InputSvg,

    [Parameter(Mandatory = $true)]
    [string]$OutputPng,

    [double]$Scale = 2.0
)

$ErrorActionPreference = "Stop"

$Script = Join-Path $PSScriptRoot "render_svg_png.js"
if (!(Test-Path -LiteralPath $Script)) {
    throw "Missing renderer script: $Script"
}

node $Script $InputSvg $OutputPng $Scale
if ($LASTEXITCODE -ne 0) {
    throw "SVG to PNG rendering failed with exit code $LASTEXITCODE"
}
