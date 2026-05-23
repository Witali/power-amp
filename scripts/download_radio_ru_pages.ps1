param(
    [Parameter(Mandatory = $true)]
    [string[]]$Pages,
    [string]$OutDir = ".tmp\archive_radio_ru",
    [switch]$Refresh
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$OutputRoot = Join-Path $Root $OutDir
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

function Get-ArchiveRadioRuPagePath {
    param(
        [string]$CacheRoot,
        [string]$Year,
        [string]$Month,
        [string]$Page
    )

    $monthDir = Join-Path (Join-Path $CacheRoot $Year) $Month
    New-Item -ItemType Directory -Force -Path $monthDir | Out-Null
    return Join-Path $monthDir "b.$Year-$Month.$Page.jpg"
}

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
        $dest = Get-ArchiveRadioRuPagePath -CacheRoot $OutputRoot -Year $year -Month $month -Page $page

        if ((Test-Path -LiteralPath $dest) -and !$Refresh) {
            Write-Host "Cached $pageSpec -> $dest"
            continue
        }

        Write-Host "Downloading $url -> $dest"
        Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
    }
}
