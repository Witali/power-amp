param(
    [int]$FromYear = 1970,
    [int]$ToYear = 1960,
    [int]$TailPages = 16,
    [int]$OcrTimeoutSeconds = 300,
    [int]$MaxParallelOcr = 0,
    [int]$TesseractThreadLimit = 0,
    [int]$OcrPollMilliseconds = 250,
    [string]$OutDir = ".tmp\pre1971\annual_contents",
    [string]$PageImageCacheRoot = ".tmp\archive_radio_ru",
    [ValidateSet("prose", "technical", "sauvola")]
    [string]$OcrProfile = "prose",
    [switch]$Refresh,
    [switch]$NoProgress
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Tesseract = Join-Path $Root "local_tools\Tesseract-extracted\tesseract.exe"
$TessData = Join-Path $Root "local_tools\Tesseract-extracted\tessdata"
$OutputRoot = Join-Path $Root $OutDir
$PageImageCache = Join-Path $Root $PageImageCacheRoot
$UserWordsPath = Join-Path $Root "ocr_tools\radio_ru_user_words.txt"
$PipelineParallelismScript = Join-Path $PSScriptRoot "pipeline_parallelism.ps1"

if (!(Test-Path -LiteralPath $Tesseract)) {
    throw "Tesseract not found at $Tesseract"
}
if (!(Test-Path -LiteralPath $TessData)) {
    throw "Tessdata not found at $TessData"
}
if (!(Test-Path -LiteralPath $UserWordsPath)) {
    throw "OCR user words file not found at $UserWordsPath"
}
if (!(Test-Path -LiteralPath $PipelineParallelismScript)) {
    throw "Pipeline parallelism helper not found at $PipelineParallelismScript"
}
. $PipelineParallelismScript

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
New-Item -ItemType Directory -Force -Path $PageImageCache | Out-Null

$PipelineParallelism = Get-PipelineParallelismConfig -ProjectRoot $Root
$hitPattern = [regex]"(?i)(УМЗЧ|УНЧ|усилител|низк[а-яё]*\s+частот|звуков[а-яё]*\s+частот|мощност[а-яё]*\s+звуков|стереофоническ|электрофон)"
$markerPattern = [regex]"(?i)(содержан|оглавлен|радио\s+за|перечень|алфавитн)"
$hits = New-Object System.Collections.Generic.List[object]
$markers = New-Object System.Collections.Generic.List[object]
$pages = New-Object System.Collections.Generic.List[object]
$ocrTasks = New-Object System.Collections.Generic.List[object]
$EffectiveMaxParallelOcr = if ($MaxParallelOcr -gt 0) {
    $MaxParallelOcr
}
else {
    $PipelineParallelism.MaxParallelOcrTasks
}
$EffectiveMaxParallelOcr = [Math]::Max(1, $EffectiveMaxParallelOcr)
$TesseractThreadLimit = if ($TesseractThreadLimit -gt 0) {
    $TesseractThreadLimit
}
else {
    $PipelineParallelism.TesseractThreadsPerProcess
}
$TesseractThreadLimit = [Math]::Max(1, $TesseractThreadLimit)
$OcrPollMilliseconds = [Math]::Max(50, $OcrPollMilliseconds)
$ProgressEnabled = !$NoProgress
$script:OcrTotal = 0
$script:OcrStarted = 0
$script:OcrCompleted = 0
$script:OcrSkipped = 0
$script:OcrFailed = 0

function Get-OcrProfileConfig {
    param([string]$Name)

    switch ($Name) {
        "prose" {
            [pscustomobject]@{
                Name = "prose"
                Psm = 4
                Variables = @{
                    user_defined_dpi = "300"
                    preserve_interword_spaces = "1"
                }
                UserWords = $true
            }
            break
        }
        "technical" {
            [pscustomobject]@{
                Name = "technical"
                Psm = 6
                Variables = @{
                    user_defined_dpi = "300"
                    preserve_interword_spaces = "1"
                    load_system_dawg = "0"
                    load_freq_dawg = "0"
                }
                UserWords = $true
            }
            break
        }
        "sauvola" {
            [pscustomobject]@{
                Name = "sauvola"
                Psm = 4
                Variables = @{
                    user_defined_dpi = "300"
                    preserve_interword_spaces = "1"
                    thresholding_method = "2"
                    thresholding_window_size = "0.25"
                    thresholding_kfactor = "0.34"
                }
                UserWords = $true
            }
            break
        }
        default {
            throw "Unknown OCR profile: $Name"
        }
    }
}

$SelectedOcrProfile = Get-OcrProfileConfig -Name $OcrProfile

function Write-ProgressLog {
    param([string]$Message)

    if ($ProgressEnabled) {
        $timestamp = Get-Date -Format "HH:mm:ss"
        Write-Host "[$timestamp] $Message"
    }
}

function Show-StepProgress {
    param(
        [int]$Id,
        [string]$Activity,
        [string]$Status,
        [int]$Current = 0,
        [int]$Total = 0
    )

    if (!$ProgressEnabled) {
        return
    }

    if ($Total -gt 0) {
        $percent = [Math]::Min(100, [Math]::Max(0, [int][Math]::Round(($Current / [double]$Total) * 100)))
        Write-Progress -Id $Id -Activity $Activity -Status $Status -PercentComplete $percent
    }
    else {
        Write-Progress -Id $Id -Activity $Activity -Status $Status
    }
}

function Complete-StepProgress {
    param(
        [int]$Id,
        [string]$Activity
    )

    if ($ProgressEnabled) {
        Write-Progress -Id $Id -Activity $Activity -Completed
    }
}

function Show-OcrProgress {
    param([string]$StatusPrefix = "OCR")

    $done = $script:OcrCompleted + $script:OcrSkipped
    $status = "${StatusPrefix}: $done/$($script:OcrTotal) done, started $($script:OcrStarted), skipped $($script:OcrSkipped), failed $($script:OcrFailed)"
    Show-StepProgress -Id 3 -Activity "Running Tesseract OCR" -Status $status -Current $done -Total $script:OcrTotal
}

function Download-IfNeeded {
    param(
        [string]$Uri,
        [string]$Path
    )

    if ($Refresh -or !(Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Path) | Out-Null
        Invoke-WebRequest -Uri $Uri -OutFile $Path -UseBasicParsing
    }
}

function Get-ArchiveRadioRuPageImagePath {
    param(
        [int]$Year,
        [string]$Issue,
        [string]$PageId,
        [string]$Kind = "b"
    )

    $yearText = $Year.ToString()
    $monthDir = Join-Path (Join-Path $PageImageCache $yearText) $Issue
    New-Item -ItemType Directory -Force -Path $monthDir | Out-Null
    return Join-Path $monthDir "$Kind.$yearText-$Issue.$PageId.jpg"
}

function ConvertTo-AbsoluteArchiveUrl {
    param(
        [string]$BaseUri,
        [string]$Href
    )

    $cleanHref = [System.Net.WebUtility]::HtmlDecode($Href)
    $baseWithSlash = if ($BaseUri.EndsWith("/")) { $BaseUri } else { "$BaseUri/" }
    return ([System.Uri]::new([System.Uri]$baseWithSlash, $cleanHref)).AbsoluteUri
}

function Get-ArchiveLargePageImage {
    param(
        [int]$Year,
        [string]$Issue,
        [string]$PageId,
        [string]$PageUrl,
        [string]$PageHtmlPath,
        [string]$ViewerHtmlPath
    )

    Download-IfNeeded -Uri $PageUrl -Path $PageHtmlPath
    $pageHtml = Get-Content -LiteralPath $PageHtmlPath -Raw -Encoding UTF8

    $viewerHref = $null
    foreach ($match in [regex]::Matches($pageHtml, "href\s*=\s*[""']([^""']+)[""']", "IgnoreCase")) {
        $href = $match.Groups[1].Value
        if ($href -match "(^|/)v$PageId(?:$|[?#])" -or $href -match "(^|\.\./)v$PageId(?:$|[?#])") {
            $viewerHref = $href
            break
        }
    }

    if (!$viewerHref) {
        throw "Large-page viewer link v$PageId not found on $PageUrl"
    }

    $viewerUri = ConvertTo-AbsoluteArchiveUrl -BaseUri $PageUrl -Href $viewerHref
    Download-IfNeeded -Uri $viewerUri -Path $ViewerHtmlPath
    $viewerHtml = Get-Content -LiteralPath $ViewerHtmlPath -Raw -Encoding UTF8

    $largeImageHref = $null
    $expectedLargeName = "b.$Year-$Issue.$PageId.jpg"
    foreach ($match in [regex]::Matches($viewerHtml, "src\s*=\s*[""']([^""']+)[""']", "IgnoreCase")) {
        $src = $match.Groups[1].Value
        if ($src -like "*$expectedLargeName*") {
            $largeImageHref = $src
            break
        }
        if (!$largeImageHref -and $src -match "/b\.[^/]+\.jpg(?:$|[?#])") {
            $largeImageHref = $src
        }
    }

    if (!$largeImageHref) {
        throw "Large b.* image link not found on $viewerUri"
    }

    [pscustomobject]@{
        ViewerUri = $viewerUri
        ImageUri = ConvertTo-AbsoluteArchiveUrl -BaseUri $viewerUri -Href $largeImageHref
    }
}

function Get-ContextLine {
    param(
        [string[]]$Lines,
        [int]$Index
    )

    $from = [Math]::Max(0, $Index - 1)
    $to = [Math]::Min($Lines.Length - 1, $Index + 1)
    (($Lines[$from..$to] | ForEach-Object { ($_ -replace "\s+", " ").Trim() }) -join " / ").Trim()
}

function New-TesseractPageTask {
    param(
        [string]$ImagePath,
        [string]$OutBase,
        [string]$PageLabel
    )

    [pscustomobject]@{
        ImagePath = $ImagePath
        OutBase = $OutBase
        PageLabel = $PageLabel
        TextPath = "$OutBase.txt"
    }
}

function Start-TesseractPageTask {
    param([pscustomobject]$Task)

    $profile = $Task.Profile
    $arguments = @(
        $Task.ImagePath,
        $Task.OutBase,
        "--tessdata-dir",
        $TessData,
        "-l",
        "rus+eng",
        "--psm",
        $profile.Psm,
        "--oem",
        "1"
    )
    if ($profile.UserWords) {
        $arguments += @("--user-words", $UserWordsPath)
    }
    foreach ($key in ($profile.Variables.Keys | Sort-Object)) {
        $arguments += @("-c", "$key=$($profile.Variables[$key])")
    }

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $Tesseract
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.EnvironmentVariables["OMP_THREAD_LIMIT"] = $TesseractThreadLimit.ToString()
    foreach ($argument in $arguments) {
        [void]$startInfo.ArgumentList.Add($argument)
    }

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    [void]$process.Start()

    $Task | Add-Member -NotePropertyName Process -NotePropertyValue $process -Force
    $Task | Add-Member -NotePropertyName StdoutTask -NotePropertyValue $process.StandardOutput.ReadToEndAsync() -Force
    $Task | Add-Member -NotePropertyName StderrTask -NotePropertyValue $process.StandardError.ReadToEndAsync() -Force
    $Task | Add-Member -NotePropertyName StartedAt -NotePropertyValue ([DateTime]::UtcNow) -Force
    return $Task
}

function Complete-TesseractPageTask {
    param([pscustomobject]$Task)

    $Task.Process.WaitForExit()
    $stdout = $Task.StdoutTask.GetAwaiter().GetResult()
    $stderr = $Task.StderrTask.GetAwaiter().GetResult()

    if ($Task.Process.ExitCode -ne 0) {
        $details = (($stderr, $stdout) | Where-Object { $_ } | Select-Object -First 1)
        if (!$details) {
            $details = "no diagnostic output"
        }
        Write-Warning "OCR failed on $($Task.PageLabel) with exit code $($Task.Process.ExitCode): $details"
        return $false
    }

    return $true
}

function Stop-TesseractPageTask {
    param([pscustomobject]$Task)

    Stop-Process -Id $Task.Process.Id -Force -ErrorAction SilentlyContinue
    try {
        $Task.Process.WaitForExit()
        [void]$Task.StdoutTask.GetAwaiter().GetResult()
        [void]$Task.StderrTask.GetAwaiter().GetResult()
    }
    catch {
    }
    Write-Warning "OCR timeout on $($Task.PageLabel) after $OcrTimeoutSeconds seconds"
}

function Wait-TesseractPageSlot {
    param([System.Collections.Generic.List[object]]$Running)

    while ($Running.Count -gt 0) {
        for ($i = $Running.Count - 1; $i -ge 0; $i--) {
            $task = $Running[$i]
            if ($OcrTimeoutSeconds -gt 0 -and !$task.Process.HasExited) {
                $elapsed = ([DateTime]::UtcNow - $task.StartedAt).TotalSeconds
                if ($elapsed -gt $OcrTimeoutSeconds) {
                    Stop-TesseractPageTask -Task $task
                    $script:OcrCompleted++
                    $script:OcrFailed++
                    $Running.RemoveAt($i)
                    Show-OcrProgress -StatusPrefix "Timeout $($task.PageLabel)"
                    return
                }
            }

            if ($task.Process.HasExited) {
                $ok = Complete-TesseractPageTask -Task $task
                $script:OcrCompleted++
                if (!$ok) {
                    $script:OcrFailed++
                }
                $Running.RemoveAt($i)
                Show-OcrProgress -StatusPrefix "Finished $($task.PageLabel)"
                return
            }
        }

        Start-Sleep -Milliseconds $OcrPollMilliseconds
    }
}

function Invoke-TesseractPageBatch {
    param([object[]]$Tasks)

    $running = New-Object System.Collections.Generic.List[object]
    $script:OcrTotal = $Tasks.Count
    $script:OcrStarted = 0
    $script:OcrCompleted = 0
    $script:OcrSkipped = 0
    $script:OcrFailed = 0
    if ($script:OcrTotal -eq 0) {
        Write-ProgressLog "OCR queue is empty; all selected pages already have cached text."
        return
    }

    Write-ProgressLog "OCR queue: $($script:OcrTotal) page task(s), profile $($SelectedOcrProfile.Name), max parallel $EffectiveMaxParallelOcr, per-process threads $TesseractThreadLimit."
    Show-OcrProgress -StatusPrefix "Starting"
    foreach ($task in $Tasks) {
        if (!$Refresh -and (Test-Path -LiteralPath $task.TextPath) -and ((Get-Item -LiteralPath $task.TextPath).Length -gt 0)) {
            $script:OcrSkipped++
            Show-OcrProgress -StatusPrefix "Cached $($task.PageLabel)"
            continue
        }

        while ($running.Count -ge $EffectiveMaxParallelOcr) {
            Wait-TesseractPageSlot -Running $running
        }

        $script:OcrStarted++
        $running.Add((Start-TesseractPageTask -Task $task))
        Show-OcrProgress -StatusPrefix "Started $($task.PageLabel)"
    }

    while ($running.Count -gt 0) {
        Wait-TesseractPageSlot -Running $running
    }
    Complete-StepProgress -Id 3 -Activity "Running Tesseract OCR"
    Write-ProgressLog "OCR complete: $($script:OcrCompleted) processed, $($script:OcrSkipped) cached, $($script:OcrFailed) failed."
}

function Invoke-TesseractPage {
    param(
        [string]$ImagePath,
        [string]$OutBase,
        [string]$PageLabel
    )

    $task = New-TesseractPageTask -ImagePath $ImagePath -OutBase $OutBase -PageLabel $PageLabel
    Invoke-TesseractPageBatch -Tasks @($task)
    if (!(Test-Path -LiteralPath $task.TextPath)) {
        return $false
    }

    return $true
}

if ($FromYear -lt $ToYear) {
    throw "FromYear must be greater than or equal to ToYear."
}

$yearsToScan = @($FromYear..$ToYear)
$yearCounter = 0
Write-ProgressLog "Scanning December annual contents from $FromYear down to $ToYear; tail pages per issue: $TailPages; OCR profile: $($SelectedOcrProfile.Name)."

foreach ($year in $yearsToScan) {
    $yearCounter++
    Show-StepProgress -Id 1 -Activity "Scanning December issues" -Status "$year/12 ($yearCounter/$($yearsToScan.Count))" -Current $yearCounter -Total $yearsToScan.Count
    $yearDir = Join-Path $OutputRoot "$year-12"
    New-Item -ItemType Directory -Force -Path $yearDir | Out-Null

    $issueUrl = "https://archive.radio.ru/web/$year/12/"
    $htmlPath = Join-Path $yearDir "issue.html"

    try {
        Write-ProgressLog "[$year] Downloading issue page: $issueUrl"
        Download-IfNeeded -Uri $issueUrl -Path $htmlPath
    }
    catch {
        Write-Warning "Cannot download issue page for ${year}: $($_.Exception.Message)"
        continue
    }

    $html = Get-Content -LiteralPath $htmlPath -Raw -Encoding UTF8
    $pageIndexes = [regex]::Matches($html, "p\.$year-12\.(\d{3})\.jpg") |
        ForEach-Object { [int]$_.Groups[1].Value } |
        Sort-Object -Unique

    if (!$pageIndexes) {
        Write-Warning "No page images found for $year"
        continue
    }

    $maxImageIndex = ($pageIndexes | Measure-Object -Maximum).Maximum
    $lastPrintedIndex = [Math]::Max(2, $maxImageIndex - 2)
    $firstTailIndex = [Math]::Max(2, $lastPrintedIndex - $TailPages + 1)
    $selectedIndexes = @($pageIndexes | Where-Object { $_ -ge $firstTailIndex -and $_ -le $lastPrintedIndex })
    $pageCounter = 0
    $queuedBeforeYear = $ocrTasks.Count
    Write-ProgressLog "[$year] Selected $($selectedIndexes.Count) tail page(s): $firstTailIndex..$lastPrintedIndex."

    foreach ($pageIndex in $selectedIndexes) {
        $pageCounter++
        $pageId = "{0:D3}" -f $pageIndex
        $pageUrl = "https://archive.radio.ru/web/$year/12/$pageId"
        $pageHtmlPath = Join-Path $yearDir "page.$year-12.$pageId.html"
        $viewerHtmlPath = Join-Path $yearDir "viewer.$year-12.$pageId.html"
        $imagePath = Get-ArchiveRadioRuPageImagePath -Year $year -Issue "12" -PageId $pageId -Kind "b"
        $imageUrl = $null
        $fullImageUrl = "https://archive.radio.ru/web/img/$year/f.$year-12.$pageId.jpg"
        $thumbImageUrl = "https://archive.radio.ru/web/img/$year/p.$year-12.$pageId.jpg"
        Show-StepProgress -Id 2 -Activity "Downloading selected page images" -Status "$year/12 page $pageId ($pageCounter/$($selectedIndexes.Count))" -Current $pageCounter -Total $selectedIndexes.Count

        try {
            $largeImage = Get-ArchiveLargePageImage -Year $year -Issue "12" -PageId $pageId -PageUrl $pageUrl -PageHtmlPath $pageHtmlPath -ViewerHtmlPath $viewerHtmlPath
            $imageUrl = $largeImage.ImageUri
            Write-ProgressLog "[$year/$pageId] Downloading large scan from preview link: $imageUrl"
            Download-IfNeeded -Uri $imageUrl -Path $imagePath
        }
        catch {
            Write-Warning "Large scan failed for $year/$pageId, trying regular scan: $($_.Exception.Message)"
            $imagePath = Get-ArchiveRadioRuPageImagePath -Year $year -Issue "12" -PageId $pageId -Kind "f"
            $imageUrl = $fullImageUrl
            try {
                Download-IfNeeded -Uri $fullImageUrl -Path $imagePath
            }
            catch {
                Write-Warning "Regular page failed for $year/$pageId, trying thumbnail: $($_.Exception.Message)"
                $imagePath = Get-ArchiveRadioRuPageImagePath -Year $year -Issue "12" -PageId $pageId -Kind "p"
                $imageUrl = $thumbImageUrl
                try {
                    Download-IfNeeded -Uri $thumbImageUrl -Path $imagePath
                }
                catch {
                    Write-Warning "Cannot download page ${year}/${pageId}: $($_.Exception.Message)"
                    continue
                }
            }
        }

        $outBase = Join-Path $yearDir "ocr.$year-12.$pageId"
        $textPath = "$outBase.txt"
        $textItem = Get-Item -LiteralPath $textPath -ErrorAction SilentlyContinue
        $imageItem = Get-Item -LiteralPath $imagePath -ErrorAction SilentlyContinue
        $needsOcr = $Refresh -or !$textItem -or ($textItem.Length -eq 0) -or ($imageItem -and $textItem.LastWriteTime -lt $imageItem.LastWriteTime)
        if ($needsOcr) {
            $ocrTasks.Add((New-TesseractPageTask -ImagePath $imagePath -OutBase $outBase -PageLabel "$year/$pageId"))
            $ocrTasks[$ocrTasks.Count - 1] | Add-Member -NotePropertyName Profile -NotePropertyValue $SelectedOcrProfile -Force
        }

        $pages.Add([pscustomobject]@{
            Year = $year
            PageId = $pageId
            PageUrl = $pageUrl
            ImagePath = $imagePath
            ImageUrl = $imageUrl
            TextPath = $textPath
        })
    }
    Complete-StepProgress -Id 2 -Activity "Downloading selected page images"
    $queuedThisYear = $ocrTasks.Count - $queuedBeforeYear
    Write-ProgressLog "[$year] Page scan complete: $($selectedIndexes.Count) image(s), $queuedThisYear new OCR task(s), $($pages.Count) total page record(s)."
}
Complete-StepProgress -Id 1 -Activity "Scanning December issues"

Invoke-TesseractPageBatch -Tasks $ocrTasks.ToArray()

$pageAnalyzeCounter = 0
Write-ProgressLog "Analyzing OCR text from $($pages.Count) page record(s)."
foreach ($page in $pages) {
        $pageAnalyzeCounter++
        Show-StepProgress -Id 4 -Activity "Analyzing OCR text" -Status "$($page.Year)/12 page $($page.PageId) ($pageAnalyzeCounter/$($pages.Count))" -Current $pageAnalyzeCounter -Total $pages.Count
        $year = $page.Year
        $pageId = $page.PageId
        $pageUrl = $page.PageUrl
        $textPath = $page.TextPath

        if (!(Test-Path -LiteralPath $textPath)) {
            continue
        }

        $text = Get-Content -LiteralPath $textPath -Raw -Encoding UTF8
        $lines = $text -split "\r?\n"

        for ($i = 0; $i -lt $lines.Length; $i++) {
            $line = ($lines[$i] -replace "\s+", " ").Trim()
            if (!$line) {
                continue
            }

            if ($markerPattern.IsMatch($line)) {
                $markers.Add([pscustomobject]@{
                    Year = $year
                    Issue = "12"
                    PageId = $pageId
                    PageUrl = $pageUrl
                    Line = $line
                })
            }

            if ($hitPattern.IsMatch($line)) {
                $hits.Add([pscustomobject]@{
                    Year = $year
                    Issue = "12"
                    PageId = $pageId
                    PageUrl = $pageUrl
                    Text = $line
                    Context = Get-ContextLine -Lines $lines -Index $i
                })
            }
        }
}
Complete-StepProgress -Id 4 -Activity "Analyzing OCR text"
Write-ProgressLog "Analysis complete: $($hits.Count) amplifier hit(s), $($markers.Count) contents marker(s)."

$hitsPath = Join-Path $OutputRoot "hits.tsv"
$markersPath = Join-Path $OutputRoot "markers.tsv"
$mdPath = Join-Path $OutputRoot "hits.md"

$hits | Sort-Object Year, PageId, Text | Export-Csv -LiteralPath $hitsPath -Delimiter "`t" -NoTypeInformation -Encoding UTF8
$markers | Sort-Object Year, PageId, Line | Export-Csv -LiteralPath $markersPath -Delimiter "`t" -NoTypeInformation -Encoding UTF8

$md = New-Object System.Collections.Generic.List[string]
$md.Add("# Radio.ru annual contents amplifier hits")
$md.Add("")
$md.Add("Searched December annual contents pages from $FromYear down to $ToYear. Tail pages per issue: $TailPages.")
$md.Add("")
$md.Add("| Year | December page | OCR hit | Context |")
$md.Add("|---:|---|---|---|")
foreach ($hit in ($hits | Sort-Object -Property @{ Expression = "Year"; Descending = $true }, PageId, Text)) {
    $text = ($hit.Text -replace "\|", "\|")
    $context = ($hit.Context -replace "\|", "\|")
    $md.Add("| $($hit.Year) | [$($hit.PageId)]($($hit.PageUrl)) | $text | $context |")
}
$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

[pscustomobject]@{
    Years = "$FromYear-$ToYear"
    TailPages = $TailPages
    Hits = $hits.Count
    Markers = $markers.Count
    HitsFile = $hitsPath
    MarkersFile = $markersPath
    MarkdownFile = $mdPath
}
