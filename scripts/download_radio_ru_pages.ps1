param(
    [Parameter(Mandatory = $true)]
    [string[]]$Pages,
    [string]$OutDir = "_tmp_radio_ru\article_pages",
    [switch]$Refresh
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$OutputRoot = Join-Path $Root $OutDir
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

foreach ($rawPageSpec in $Pages) {
    foreach ($pageSpec in ($rawPageSpec -split ",")) {
        $pageSpec = $pageSpec.Trim()
        if (!$pageSpec) {
            continue
        }

        if ($pageSpec -notmatch "^(\d{4})-(\d{2})-(\d{3})$") {
            throw "Page must be in YYYY-MM-PPP form: $pageSpec"
        }

        $year = $Matches[1]
        $month = $Matches[2]
        $page = $Matches[3]
        $url = "https://archive.radio.ru/web/img/$year/b.$year-$month.$page.jpg"
        $dest = Join-Path $OutputRoot "b.$year-$month.$page.jpg"

        if ((Test-Path -LiteralPath $dest) -and !$Refresh) {
            Write-Host "Cached $pageSpec"
            continue
        }

        Write-Host "Downloading $url"
        Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
    }
}
