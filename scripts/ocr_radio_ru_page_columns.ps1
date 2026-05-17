param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath,
    [string]$OutDir = ".tmp\ocr_column_trials",
    [object[]]$ColumnCounts = @(1, 2, 3),
    [object[]]$PsmModes = @(3, 4, 6),
    [object[]]$OcrProfiles = @("prose", "technical", "sauvola"),
    [double]$TopCrop = 0.02,
    [double]$BottomCrop = 0.02,
    [double]$LeftCrop = 0.04,
    [double]$RightCrop = 0.04,
    [double]$ColumnGap = 0.018,
    [switch]$AutoColumns,
    [switch]$AutoOnly,
    [int]$AutoMaxColumns = 3,
    [int]$ProjectionSampleStep = 3,
    [double]$AutoGapLowInkRatio = 0.06,
    [int]$AutoMinGapPx = 22,
    [double]$AutoMinColumnFraction = 0.18,
    [int]$AutoSplitPaddingPx = 8,
    [switch]$NoAutoInvert,
    [switch]$NoTextCorrection,
    [switch]$DetectLayout,
    [string]$LayoutOutDir = ".tmp\page_layout",
    [int]$MaxParallelOcr = 0,
    [int]$TesseractThreadLimit = 1,
    [int]$OcrPollMilliseconds = 250,
    [switch]$Refresh,
    [switch]$NoProgress
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Tesseract = Join-Path $Root "local_tools\Tesseract-extracted\tesseract.exe"
$TessData = Join-Path $Root "local_tools\Tesseract-extracted\tessdata"
$OutputRoot = Join-Path $Root $OutDir
$CorrectionScript = Join-Path $PSScriptRoot "radio_ru_ocr_corrections.ps1"
$UserWordsPath = Join-Path $Root "ocr_tools\radio_ru_user_words.txt"

if (!(Test-Path -LiteralPath $Tesseract)) {
    throw "Tesseract not found at $Tesseract"
}
if (!(Test-Path -LiteralPath $TessData)) {
    throw "Tessdata not found at $TessData"
}
if (!$NoTextCorrection -and !(Test-Path -LiteralPath $CorrectionScript)) {
    throw "OCR correction script not found at $CorrectionScript"
}
if (!(Test-Path -LiteralPath $UserWordsPath)) {
    throw "OCR user words file not found at $UserWordsPath"
}
if (!$NoTextCorrection) {
    . $CorrectionScript
}

Add-Type -AssemblyName System.Drawing

if (!("RadioRuOcrLayout" -as [type])) {
    Add-Type -ReferencedAssemblies System.Drawing,System.Drawing.Common,System.Drawing.Primitives,System.Collections,System.Linq,System.Core,System.Private.Windows.GdiPlus,System.Private.Windows.Core -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;

public sealed class RadioRuProjectionResult
{
    public int Threshold;
    public bool BrightForeground;
    public int[] Density;
    public int[] Splits;
    public int MaxDensity;
    public int LowDensityLimit;
}

public static class RadioRuOcrLayout
{
    private sealed class GapRun
    {
        public int Start;
        public int End;
        public int Width { get { return End - Start + 1; } }
        public int Center { get { return (Start + End) / 2; } }
    }

    private static int Luma(Color color)
    {
        return (int)Math.Round(0.299 * color.R + 0.587 * color.G + 0.114 * color.B);
    }

    private static int OtsuThreshold(int[] histogram, int total)
    {
        double sum = 0;
        for (int i = 0; i < 256; i++) sum += i * histogram[i];

        double sumB = 0;
        int weightB = 0;
        double maxVariance = -1;
        int threshold = 128;

        for (int i = 0; i < 256; i++)
        {
            weightB += histogram[i];
            if (weightB == 0) continue;

            int weightF = total - weightB;
            if (weightF == 0) break;

            sumB += i * histogram[i];
            double meanB = sumB / weightB;
            double meanF = (sum - sumB) / weightF;
            double variance = weightB * weightF * Math.Pow(meanB - meanF, 2);

            if (variance > maxVariance)
            {
                maxVariance = variance;
                threshold = i;
            }
        }

        return threshold;
    }

    private static bool IsForeground(int luma, int threshold, bool brightForeground)
    {
        return brightForeground ? luma > threshold : luma <= threshold;
    }

    private static bool HasValidSegments(List<int> splits, int left, int right, int minColumnWidth)
    {
        int previous = left;
        foreach (int split in splits.OrderBy(x => x))
        {
            if (split - previous < minColumnWidth) return false;
            previous = split;
        }

        return right - previous >= minColumnWidth;
    }

    public static RadioRuProjectionResult DetectVerticalSplits(
        Bitmap image,
        Rectangle contentRect,
        int maxColumns,
        int sampleStep,
        double lowInkRatio,
        int minGapPx,
        double minColumnFraction)
    {
        maxColumns = Math.Max(1, Math.Min(4, maxColumns));
        sampleStep = Math.Max(1, sampleStep);

        int[] histogram = new int[256];
        int samples = 0;

        for (int y = contentRect.Top; y < contentRect.Bottom; y += sampleStep)
        {
            for (int x = contentRect.Left; x < contentRect.Right; x += sampleStep)
            {
                histogram[Luma(image.GetPixel(x, y))]++;
                samples++;
            }
        }

        int threshold = OtsuThreshold(histogram, samples);
        int darkCount = 0;
        for (int i = 0; i <= threshold; i++) darkCount += histogram[i];
        int lightCount = samples - darkCount;
        bool brightForeground = lightCount < darkCount;

        int[] density = new int[contentRect.Width];
        for (int x = contentRect.Left; x < contentRect.Right; x++)
        {
            int hits = 0;
            for (int y = contentRect.Top; y < contentRect.Bottom; y += sampleStep)
            {
                int luma = Luma(image.GetPixel(x, y));
                if (IsForeground(luma, threshold, brightForeground)) hits++;
            }
            density[x - contentRect.Left] = hits;
        }

        int smoothRadius = Math.Max(2, (int)Math.Round(contentRect.Width * 0.004));
        int[] smoothed = new int[density.Length];
        for (int i = 0; i < density.Length; i++)
        {
            int from = Math.Max(0, i - smoothRadius);
            int to = Math.Min(density.Length - 1, i + smoothRadius);
            int sum = 0;
            for (int j = from; j <= to; j++) sum += density[j];
            smoothed[i] = (int)Math.Round(sum / (double)(to - from + 1));
        }

        int maxDensity = smoothed.Length == 0 ? 0 : smoothed.Max();
        int lowLimit = Math.Max(1, (int)Math.Round(maxDensity * lowInkRatio));
        int edgeGuard = Math.Max(minGapPx, (int)Math.Round(contentRect.Width * 0.04));
        int minColumnWidth = Math.Max(20, (int)Math.Round(contentRect.Width * minColumnFraction));

        List<GapRun> runs = new List<GapRun>();
        int runStart = -1;
        for (int i = 0; i < smoothed.Length; i++)
        {
            bool low = smoothed[i] <= lowLimit;
            if (low && runStart < 0)
            {
                runStart = i;
            }
            else if (!low && runStart >= 0)
            {
                int runEnd = i - 1;
                if (runEnd - runStart + 1 >= minGapPx)
                {
                    runs.Add(new GapRun { Start = contentRect.Left + runStart, End = contentRect.Left + runEnd });
                }
                runStart = -1;
            }
        }

        if (runStart >= 0)
        {
            int runEnd = smoothed.Length - 1;
            if (runEnd - runStart + 1 >= minGapPx)
            {
                runs.Add(new GapRun { Start = contentRect.Left + runStart, End = contentRect.Left + runEnd });
            }
        }

        List<int> splits = new List<int>();
        foreach (GapRun run in runs.OrderByDescending(r => r.Width))
        {
            int center = run.Center;
            if (center - contentRect.Left < edgeGuard || contentRect.Right - center < edgeGuard) continue;

            List<int> trial = new List<int>(splits);
            trial.Add(center);
            trial.Sort();

            if (trial.Count <= maxColumns - 1 &&
                HasValidSegments(trial, contentRect.Left, contentRect.Right, minColumnWidth))
            {
                splits = trial;
            }

            if (splits.Count >= maxColumns - 1) break;
        }

        return new RadioRuProjectionResult
        {
            Threshold = threshold,
            BrightForeground = brightForeground,
            Density = smoothed,
            Splits = splits.OrderBy(x => x).ToArray(),
            MaxDensity = maxDensity,
            LowDensityLimit = lowLimit
        };
    }

    public static void SaveCropNormalized(Bitmap image, Rectangle rect, string path, bool autoInvertDark)
    {
        using (Bitmap crop = new Bitmap(rect.Width, rect.Height, PixelFormat.Format24bppRgb))
        {
            using (Graphics graphics = Graphics.FromImage(crop))
            {
                graphics.DrawImage(image, new Rectangle(0, 0, rect.Width, rect.Height), rect, GraphicsUnit.Pixel);
            }

            if (autoInvertDark && AverageLuma(crop) < 128.0)
            {
                for (int y = 0; y < crop.Height; y++)
                {
                    for (int x = 0; x < crop.Width; x++)
                    {
                        Color c = crop.GetPixel(x, y);
                        crop.SetPixel(x, y, Color.FromArgb(255 - c.R, 255 - c.G, 255 - c.B));
                    }
                }
            }

            Directory.CreateDirectory(Path.GetDirectoryName(path));
            crop.Save(path, ImageFormat.Png);
        }
    }

    private static double AverageLuma(Bitmap image)
    {
        long sum = 0;
        int count = 0;
        int step = Math.Max(1, Math.Min(image.Width, image.Height) / 80);
        for (int y = 0; y < image.Height; y += step)
        {
            for (int x = 0; x < image.Width; x += step)
            {
                sum += Luma(image.GetPixel(x, y));
                count++;
            }
        }

        return count == 0 ? 255.0 : sum / (double)count;
    }
}
"@
}

function Convert-ToIntList {
    param(
        [object[]]$Values,
        [int[]]$DefaultValues
    )

    $items = New-Object System.Collections.Generic.List[int]
    foreach ($value in $Values) {
        foreach ($part in (($value.ToString()) -split "[,\s]+")) {
            if (!$part) {
                continue
            }
            $items.Add([int]$part)
        }
    }

    if ($items.Count -eq 0) {
        return $DefaultValues
    }

    return @($items | Sort-Object -Unique)
}

$ColumnCounts = Convert-ToIntList -Values $ColumnCounts -DefaultValues @(1, 2, 3)
$PsmModes = Convert-ToIntList -Values $PsmModes -DefaultValues @(3, 4, 6)
$EffectiveMaxParallelOcr = if ($MaxParallelOcr -gt 0) {
    $MaxParallelOcr
}
else {
    [Math]::Max(1, [int][Math]::Floor([Environment]::ProcessorCount / 2.0))
}
$EffectiveMaxParallelOcr = [Math]::Max(1, $EffectiveMaxParallelOcr)
$TesseractThreadLimit = [Math]::Max(1, $TesseractThreadLimit)
$OcrPollMilliseconds = [Math]::Max(50, $OcrPollMilliseconds)
$ProgressEnabled = !$NoProgress
$script:OcrTotal = 0
$script:OcrStarted = 0
$script:OcrCompleted = 0
$script:OcrSkipped = 0
$script:FigureLinksText = ""

function Convert-ToStringList {
    param(
        [object[]]$Values,
        [string[]]$DefaultValues
    )

    if ($null -eq $Values -or $Values.Count -eq 0) {
        return $DefaultValues
    }

    $converted = New-Object System.Collections.Generic.List[string]
    foreach ($value in $Values) {
        if ($null -eq $value) {
            continue
        }
        foreach ($part in ($value.ToString() -split ",")) {
            $trimmed = $part.Trim()
            if ($trimmed) {
                $converted.Add($trimmed)
            }
        }
    }

    if ($converted.Count -eq 0) {
        return $DefaultValues
    }

    return @($converted)
}

function Get-OcrProfileConfig {
    param([string]$Name)

    switch ($Name) {
        "prose" {
            [pscustomobject]@{
                Name = "prose"
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

$OcrProfiles = Convert-ToStringList -Values $OcrProfiles -DefaultValues @("prose", "technical", "sauvola")
$SelectedOcrProfiles = @($OcrProfiles | ForEach-Object { Get-OcrProfileConfig -Name $_ })

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
    $status = "${StatusPrefix}: $done/$($script:OcrTotal) done, started $($script:OcrStarted), skipped $($script:OcrSkipped)"
    Show-StepProgress -Id 3 -Activity "Running column OCR" -Status $status -Current $done -Total $script:OcrTotal
}

function New-Directory {
    param([string]$Path)
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

function Save-Crop {
    param(
        [System.Drawing.Bitmap]$Image,
        [System.Drawing.Rectangle]$Rect,
        [string]$Path
    )

    [RadioRuOcrLayout]::SaveCropNormalized($Image, $Rect, $Path, !$NoAutoInvert)
}

function Save-LayoutCrop {
    param(
        [System.Drawing.Bitmap]$Image,
        [object[]]$Bbox,
        [string]$Path,
        [switch]$AutoInvert
    )

    $rect = [System.Drawing.Rectangle]::new(
        [int]$Bbox[0],
        [int]$Bbox[1],
        [int]$Bbox[2],
        [int]$Bbox[3]
    )
    [RadioRuOcrLayout]::SaveCropNormalized($Image, $rect, $Path, [bool]$AutoInvert)
}

function Escape-MarkdownCell {
    param([string]$Text)

    if ($null -eq $Text) {
        return ""
    }
    return (($Text -replace "\r?\n", " ").Replace("|", "\|")).Trim()
}

function Get-FigureRefFromText {
    param([string]$Text)

    if (!$Text) {
        return ""
    }
    $normalized = $Text -replace "\s+", " "
    $match = [regex]::Match($normalized, "(?i)(?:рис(?:унок)?|pic|fig(?:ure)?)\.?\s*[-–—]?\s*(\d+[a-zа-я]?)")
    if (!$match.Success) {
        return ""
    }
    return "Рис. $($match.Groups[1].Value)"
}

function Get-LayoutDisplayLabel {
    param([string]$Label)

    if ($Label -eq "schematic/circuit") {
        return "schematic"
    }
    return $Label
}

function Export-FigureLinks {
    param(
        [System.Drawing.Bitmap]$Image,
        [string]$LayoutPath,
        [string]$PageOutDir
    )

    $script:FigureLinksText = ""
    if (!(Test-Path -LiteralPath $LayoutPath)) {
        return
    }

    $layout = Get-Content -LiteralPath $LayoutPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $figureBlocks = @($layout.blocks | Where-Object { $_.label -in @("image", "schematic/circuit", "diagram") })
    if ($figureBlocks.Count -eq 0) {
        return
    }

    $figureDir = Join-Path $PageOutDir "layout_figures"
    New-Directory $figureDir
    $tasks = New-Object System.Collections.Generic.List[object]
    $entries = New-Object System.Collections.Generic.List[object]
    $captionProfile = Get-OcrProfileConfig -Name "technical"

    foreach ($block in $figureBlocks) {
        $figureImageName = "$($block.ident).png"
        $figureImagePath = Join-Path $figureDir $figureImageName
        Save-LayoutCrop -Image $Image -Bbox $block.bbox -Path $figureImagePath
        $figureCrop = "layout_figures/$figureImageName"

        $entry = [pscustomobject]@{
            Block = $block.ident
            Label = Get-LayoutDisplayLabel -Label $block.label
            FigureImageName = $figureImageName
            FigureCrop = $figureCrop
            CaptionBlock = ""
            CaptionText = ""
            FigureRef = ""
            CaptionImageName = ""
            CaptionCrop = ""
            CaptionPosition = ""
        }
        $entries.Add($entry)

        foreach ($candidate in @($block.caption_candidates)) {
            if ($null -eq $candidate) {
                continue
            }
            $captionBlock = $candidate.block.ToString()
            $captionBaseName = "$($block.ident).$captionBlock.caption"
            $captionImageName = "$captionBaseName.png"
            $captionImagePath = Join-Path $figureDir $captionImageName
            Save-LayoutCrop -Image $Image -Bbox $candidate.bbox -Path $captionImagePath -AutoInvert
            $task = New-TesseractTask -ImagePath $captionImagePath -OutBase (Join-Path $figureDir $captionBaseName) -Psm 7 -Profile $captionProfile
            $task | Add-Member -NotePropertyName FigureEntry -NotePropertyValue $entry -Force
            $task | Add-Member -NotePropertyName CaptionBlock -NotePropertyValue $captionBlock -Force
            $task | Add-Member -NotePropertyName CaptionImageName -NotePropertyValue $captionImageName -Force
            $task | Add-Member -NotePropertyName CaptionPosition -NotePropertyValue $candidate.position.ToString() -Force
            $tasks.Add($task)
        }
    }

    if ($tasks.Count -gt 0) {
        Write-ProgressLog "OCR figure caption candidates: $($tasks.Count) crop(s)."
        Invoke-TesseractBatch -Tasks $tasks.ToArray()
        foreach ($task in $tasks) {
            if (!(Test-Path -LiteralPath $task.TextPath)) {
                continue
            }
            $captionText = (Get-Content -LiteralPath $task.TextPath -Raw -Encoding UTF8).Trim()
            $figureRef = Get-FigureRefFromText -Text $captionText
            if ($figureRef -and !$task.FigureEntry.FigureRef) {
                $task.FigureEntry.FigureRef = $figureRef
                $task.FigureEntry.CaptionText = $captionText
                $task.FigureEntry.CaptionBlock = $task.CaptionBlock
                $task.FigureEntry.CaptionImageName = $task.CaptionImageName
                $task.FigureEntry.CaptionCrop = "layout_figures/$($task.CaptionImageName)"
                $task.FigureEntry.CaptionPosition = $task.CaptionPosition
            }
            elseif (!$task.FigureEntry.CaptionText) {
                $task.FigureEntry.CaptionText = $captionText
                $task.FigureEntry.CaptionBlock = $task.CaptionBlock
                $task.FigureEntry.CaptionImageName = $task.CaptionImageName
                $task.FigureEntry.CaptionCrop = "layout_figures/$($task.CaptionImageName)"
                $task.FigureEntry.CaptionPosition = $task.CaptionPosition
            }
        }
    }

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("## Figure links")
    $lines.Add("")
    $lines.Add("| Figure | Layout block | Label | Crop | Caption OCR |")
    $lines.Add("| --- | --- | --- | --- | --- |")
    foreach ($entry in $entries) {
        $figureRef = if ($entry.FigureRef) { $entry.FigureRef } else { "(unrecognized)" }
        $lines.Add("| $(Escape-MarkdownCell $figureRef) | $(Escape-MarkdownCell $entry.Block) | $(Escape-MarkdownCell $entry.Label) | [$($entry.FigureImageName)]($($entry.FigureCrop)) | $(Escape-MarkdownCell $entry.CaptionText) |")
    }

    $figureLinksPath = Join-Path $PageOutDir "figure_links.md"
    $figureLinksJsonPath = Join-Path $PageOutDir "figure_links.json"
    $script:FigureLinksText = ($lines -join "`r`n")
    $script:FigureLinksText | Set-Content -LiteralPath $figureLinksPath -Encoding UTF8
    @($entries | ForEach-Object {
        [pscustomobject]@{
            figure_ref = $_.FigureRef
            layout_block = $_.Block
            label = $_.Label
            crop = $_.FigureCrop
            caption_block = $_.CaptionBlock
            caption_position = $_.CaptionPosition
            caption_text = $_.CaptionText
            caption_crop = $_.CaptionCrop
        }
    }) | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $figureLinksJsonPath -Encoding UTF8
    Write-ProgressLog "Wrote figure links: $figureLinksPath"
}

function New-TesseractTask {
    param(
        [string]$ImagePath,
        [string]$OutBase,
        [int]$Psm,
        [pscustomobject]$Profile
    )

    $txtPath = "$OutBase.txt"
    [pscustomobject]@{
        ImagePath = $ImagePath
        OutBase = $OutBase
        Psm = $Psm
        Profile = $Profile
        TextPath = $txtPath
    }
}

function Start-TesseractTask {
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
        $Task.Psm,
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
    return $Task
}

function Complete-TesseractTask {
    param([pscustomobject]$Task)

    $Task.Process.WaitForExit()
    $stdout = $Task.StdoutTask.GetAwaiter().GetResult()
    $stderr = $Task.StderrTask.GetAwaiter().GetResult()

    if ($Task.Process.ExitCode -ne 0) {
        $details = (($stderr, $stdout) | Where-Object { $_ } | Select-Object -First 1)
        if (!$details) {
            $details = "no diagnostic output"
        }
        throw "Tesseract failed for $($Task.ImagePath), profile $($Task.Profile.Name), psm $($Task.Psm), exit code $($Task.Process.ExitCode): $details"
    }
}

function Wait-TesseractSlot {
    param(
        [System.Collections.Generic.List[object]]$Running,
        [switch]$Any
    )

    while ($Running.Count -gt 0) {
        for ($i = $Running.Count - 1; $i -ge 0; $i--) {
            $task = $Running[$i]
            if ($task.Process.HasExited) {
                Complete-TesseractTask -Task $task
                $script:OcrCompleted++
                $Running.RemoveAt($i)
                Show-OcrProgress -StatusPrefix "Finished $($task.Profile.Name)/psm$($task.Psm)"
                if ($Any) {
                    return
                }
            }
        }

        if ($Any) {
            Start-Sleep -Milliseconds $OcrPollMilliseconds
        }
        else {
            break
        }
    }
}

function Invoke-TesseractBatch {
    param([object[]]$Tasks)

    $running = New-Object System.Collections.Generic.List[object]
    $script:OcrTotal = $Tasks.Count
    $script:OcrStarted = 0
    $script:OcrCompleted = 0
    $script:OcrSkipped = 0
    if ($script:OcrTotal -eq 0) {
        Write-ProgressLog "OCR queue is empty for this variant."
        return
    }

    Write-ProgressLog "OCR queue: $($script:OcrTotal) crop task(s), max parallel $EffectiveMaxParallelOcr, per-process threads $TesseractThreadLimit."
    Show-OcrProgress -StatusPrefix "Starting"
    foreach ($task in $Tasks) {
        if (!$Refresh -and (Test-Path -LiteralPath $task.TextPath) -and ((Get-Item -LiteralPath $task.TextPath).Length -gt 0)) {
            $script:OcrSkipped++
            Show-OcrProgress -StatusPrefix "Cached $($task.Profile.Name)/psm$($task.Psm)"
            continue
        }

        while ($running.Count -ge $EffectiveMaxParallelOcr) {
            Wait-TesseractSlot -Running $running -Any
        }

        $script:OcrStarted++
        $running.Add((Start-TesseractTask -Task $task))
        Show-OcrProgress -StatusPrefix "Started $($task.Profile.Name)/psm$($task.Psm)"
    }

    while ($running.Count -gt 0) {
        Wait-TesseractSlot -Running $running -Any
    }
    Complete-StepProgress -Id 3 -Activity "Running column OCR"
    Write-ProgressLog "OCR variant complete: $($script:OcrCompleted) processed, $($script:OcrSkipped) cached."
}

function Invoke-Tesseract {
    param(
        [string]$ImagePath,
        [string]$OutBase,
        [int]$Psm,
        [pscustomobject]$Profile
    )

    $txtPath = "$OutBase.txt"
    if (!$Refresh -and (Test-Path -LiteralPath $txtPath) -and ((Get-Item -LiteralPath $txtPath).Length -gt 0)) {
        return
    }

    Invoke-TesseractBatch -Tasks @((New-TesseractTask -ImagePath $ImagePath -OutBase $OutBase -Psm $Psm -Profile $Profile))
}

function Get-TextScore {
    param([string]$Text)

    $lines = $Text -split "\r?\n" | ForEach-Object { ($_ -replace "\s+", " ").Trim() } | Where-Object { $_ }
    $cyrillic = ([regex]::Matches($Text, "[А-Яа-яЁё]")).Count
    $latin = ([regex]::Matches($Text, "[A-Za-z]")).Count
    $digits = ([regex]::Matches($Text, "\d")).Count
    $articleWords = ([regex]::Matches($Text, "(?i)усилител|транзистор|звуко|НЧ|магнитофон|электроакуст")).Count
    $leaderLines = ($lines | Where-Object { $_ -match "\.{2,}|\s+\d{1,2}\s+\d{1,2}" }).Count
    $longLines = ($lines | Where-Object { $_.Length -gt 130 }).Count

    [pscustomobject]@{
        Lines = $lines.Count
        Cyrillic = $cyrillic
        Latin = $latin
        Digits = $digits
        ArticleWords = $articleWords
        LeaderLines = $leaderLines
        LongLines = $longLines
        Score = ($cyrillic + 8 * $articleWords + 4 * $leaderLines - 10 * $longLines - 2 * $latin)
    }
}

function Get-ColumnRectsFromSplits {
    param(
        [int]$Left,
        [int]$Top,
        [int]$Right,
        [int]$Bottom,
        [int[]]$Splits,
        [int]$SplitPadding
    )

    $rects = New-Object System.Collections.Generic.List[System.Drawing.Rectangle]
    $start = $Left
    $orderedSplits = @($Splits | Sort-Object)

    for ($i = 0; $i -lt $orderedSplits.Count; $i++) {
        $end = [Math]::Max($start + 1, $orderedSplits[$i] - $SplitPadding)
        $rects.Add([System.Drawing.Rectangle]::new($start, $Top, $end - $start, $Bottom - $Top))
        $start = [Math]::Min($Right - 1, $orderedSplits[$i] + $SplitPadding)
    }

    if ($Right - $start -gt 1) {
        $rects.Add([System.Drawing.Rectangle]::new($start, $Top, $Right - $start, $Bottom - $Top))
    }

    return @($rects)
}

function Invoke-OcrVariant {
    param(
        [System.Drawing.Bitmap]$Image,
        [string]$VariantDir,
        [System.Drawing.Rectangle[]]$ColumnRects,
        [int[]]$PsmModes,
        [object[]]$Profiles
    )

    New-Directory $VariantDir
    $columnImages = New-Object System.Collections.Generic.List[string]
    Write-ProgressLog "Preparing OCR variant '$([IO.Path]::GetFileName($VariantDir))': $($ColumnRects.Count) column(s), $($PsmModes.Count) PSM mode(s), profiles: $(@($Profiles | ForEach-Object { $_.Name }) -join ', ')."

    for ($column = 0; $column -lt $ColumnRects.Count; $column++) {
        Show-StepProgress -Id 2 -Activity "Saving OCR column crops" -Status "column $($column + 1)/$($ColumnRects.Count)" -Current ($column + 1) -Total $ColumnRects.Count
        $cropPath = Join-Path $VariantDir ("column{0}.png" -f ($column + 1))
        Save-Crop -Image $Image -Rect $ColumnRects[$column] -Path $cropPath
        $columnImages.Add($cropPath)
    }
    Complete-StepProgress -Id 2 -Activity "Saving OCR column crops"

    $tasks = New-Object System.Collections.Generic.List[object]
    foreach ($profile in $Profiles) {
        foreach ($psm in $PsmModes) {
            for ($column = 0; $column -lt $columnImages.Count; $column++) {
                $outBase = Join-Path $VariantDir ("column{0}.{1}.psm{2}" -f ($column + 1), $profile.Name, $psm)
                $tasks.Add((New-TesseractTask -ImagePath $columnImages[$column] -OutBase $outBase -Psm $psm -Profile $profile))
            }
        }
    }
    Invoke-TesseractBatch -Tasks $tasks.ToArray()

    foreach ($profile in $Profiles) {
        foreach ($psm in $PsmModes) {
            Write-ProgressLog "Merging OCR text for variant '$([IO.Path]::GetFileName($VariantDir))', profile $($profile.Name), PSM $psm."
            $parts = New-Object System.Collections.Generic.List[string]
            for ($column = 0; $column -lt $columnImages.Count; $column++) {
                $outBase = Join-Path $VariantDir ("column{0}.{1}.psm{2}" -f ($column + 1), $profile.Name, $psm)
                $txtPath = "$outBase.txt"
                if (Test-Path -LiteralPath $txtPath) {
                    $parts.Add((Get-Content -LiteralPath $txtPath -Raw -Encoding UTF8).Trim())
                }
            }

            $mergedPath = Join-Path $VariantDir ("merged.{0}.psm{1}.txt" -f $profile.Name, $psm)
            $mergedText = $parts -join "`r`n`r`n--- column ---`r`n`r`n"
            if ($script:FigureLinksText) {
                $mergedText = "$mergedText`r`n`r`n--- figures ---`r`n`r`n$script:FigureLinksText"
            }
            $mergedText | Set-Content -LiteralPath $mergedPath -Encoding UTF8
            if (!$NoTextCorrection) {
                Repair-RadioRuOcrFile -InputPath $mergedPath | Out-Null
            }
        }
    }
}

$resolvedInput = (Resolve-Path -LiteralPath $InputPath).Path
$imageName = [IO.Path]::GetFileNameWithoutExtension($resolvedInput)
$pageOutDir = Join-Path $OutputRoot $imageName
New-Directory $pageOutDir

if ($DetectLayout) {
    $layoutScript = Join-Path $PSScriptRoot "detect_page_layout.py"
    Write-ProgressLog "Running OpenCV layout detector before OCR."
    & python $layoutScript --image $resolvedInput --out-dir $LayoutOutDir
    if ($LASTEXITCODE -ne 0) {
        throw "OpenCV layout detector failed with exit code $LASTEXITCODE"
    }
}

$image = [System.Drawing.Bitmap]::FromFile($resolvedInput)
try {
    Write-ProgressLog "Processing page image: $resolvedInput"
    Write-ProgressLog "Image size: $($image.Width)x$($image.Height). Output: $pageOutDir"
    if ($DetectLayout) {
        $resolvedLayoutOutDir = if ([IO.Path]::IsPathRooted($LayoutOutDir)) { $LayoutOutDir } else { Join-Path $Root $LayoutOutDir }
        $layoutJsonPath = Join-Path (Join-Path $resolvedLayoutOutDir $imageName) "layout.json"
        Export-FigureLinks -Image $image -LayoutPath $layoutJsonPath -PageOutDir $pageOutDir
    }
    $left = [int][Math]::Round($image.Width * $LeftCrop)
    $top = [int][Math]::Round($image.Height * $TopCrop)
    $right = [int][Math]::Round($image.Width * (1.0 - $RightCrop))
    $bottom = [int][Math]::Round($image.Height * (1.0 - $BottomCrop))
    $contentWidth = $right - $left
    $contentHeight = $bottom - $top

    if (!$AutoOnly) {
        $manualCounter = 0
        Write-ProgressLog "Running manual column trials: $(@($ColumnCounts) -join ', ') column(s); PSM modes: $(@($PsmModes) -join ', '); profiles: $(@($SelectedOcrProfiles | ForEach-Object { $_.Name }) -join ', ')."
        foreach ($columnCount in $ColumnCounts) {
            $manualCounter++
            Show-StepProgress -Id 1 -Activity "Manual column trials" -Status "columns $columnCount ($manualCounter/$($ColumnCounts.Count))" -Current $manualCounter -Total $ColumnCounts.Count
            $variantDir = Join-Path $pageOutDir "columns$columnCount"
            $gap = if ($columnCount -gt 1) { [int][Math]::Round($image.Width * $ColumnGap) } else { 0 }
            $columnWidth = [int][Math]::Floor(($contentWidth - ($columnCount - 1) * $gap) / $columnCount)
            $rects = New-Object System.Collections.Generic.List[System.Drawing.Rectangle]

            for ($column = 0; $column -lt $columnCount; $column++) {
                $x = $left + $column * ($columnWidth + $gap)
                $w = if ($column -eq ($columnCount - 1)) { $right - $x } else { $columnWidth }
                $rects.Add([System.Drawing.Rectangle]::new($x, $top, $w, $contentHeight))
            }

            Invoke-OcrVariant -Image $image -VariantDir $variantDir -ColumnRects $rects.ToArray() -PsmModes $PsmModes -Profiles $SelectedOcrProfiles
        }
        Complete-StepProgress -Id 1 -Activity "Manual column trials"
    }

    if ($AutoColumns -or $AutoOnly) {
        Write-ProgressLog "Detecting automatic column splits up to $AutoMaxColumns column(s)."
        $contentRect = [System.Drawing.Rectangle]::new($left, $top, $contentWidth, $contentHeight)
        $projection = [RadioRuOcrLayout]::DetectVerticalSplits(
            $image,
            $contentRect,
            $AutoMaxColumns,
            $ProjectionSampleStep,
            $AutoGapLowInkRatio,
            $AutoMinGapPx,
            $AutoMinColumnFraction
        )

        $layoutPath = Join-Path $pageOutDir "auto_layout.tsv"
        $layoutLines = New-Object System.Collections.Generic.List[string]
        $layoutLines.Add("key`tvalue")
        $layoutLines.Add("threshold`t$($projection.Threshold)")
        $layoutLines.Add("bright_foreground`t$($projection.BrightForeground)")
        $layoutLines.Add("max_density`t$($projection.MaxDensity)")
        $layoutLines.Add("low_density_limit`t$($projection.LowDensityLimit)")
        $layoutLines.Add("splits`t$(@($projection.Splits) -join ',')")
        $layoutLines | Set-Content -LiteralPath $layoutPath -Encoding UTF8
        Write-ProgressLog "Auto layout: threshold $($projection.Threshold), bright foreground $($projection.BrightForeground), splits $(@($projection.Splits) -join ',')."

        $densityPath = Join-Path $pageOutDir "auto_density.tsv"
        $densityLines = New-Object System.Collections.Generic.List[string]
        $densityLines.Add("x`tdensity")
        for ($i = 0; $i -lt $projection.Density.Length; $i++) {
            $densityLines.Add("$($left + $i)`t$($projection.Density[$i])")
        }
        $densityLines | Set-Content -LiteralPath $densityPath -Encoding UTF8

        $maxAutoColumns = [Math]::Min($AutoMaxColumns, @($projection.Splits).Count + 1)
        $autoVariantCounter = 0
        $autoVariantTotal = [Math]::Max(0, $maxAutoColumns - 1)
        for ($columnCount = 2; $columnCount -le $maxAutoColumns; $columnCount++) {
            $autoVariantCounter++
            Show-StepProgress -Id 4 -Activity "Automatic column trials" -Status "auto columns $columnCount ($autoVariantCounter/$autoVariantTotal)" -Current $autoVariantCounter -Total $autoVariantTotal
            $splitsForVariant = @($projection.Splits | Select-Object -First ($columnCount - 1))
            $rects = Get-ColumnRectsFromSplits -Left $left -Top $top -Right $right -Bottom $bottom -Splits $splitsForVariant -SplitPadding $AutoSplitPaddingPx
            if ($rects.Count -eq $columnCount) {
                $variantDir = Join-Path $pageOutDir "auto_columns$columnCount"
                Invoke-OcrVariant -Image $image -VariantDir $variantDir -ColumnRects $rects -PsmModes $PsmModes -Profiles $SelectedOcrProfiles
            }
        }
        Complete-StepProgress -Id 4 -Activity "Automatic column trials"
    }
}
finally {
    $image.Dispose()
}

$summary = New-Object System.Collections.Generic.List[object]
$textFiles = @(Get-ChildItem -LiteralPath $pageOutDir -Recurse -Filter "merged.*.psm*.txt" | Where-Object { $_.BaseName -notmatch "\.corrected$" })
$summaryCounter = 0
Write-ProgressLog "Scoring OCR variants: $($textFiles.Count) merged text file(s)."
foreach ($textFile in $textFiles) {
    $summaryCounter++
    Show-StepProgress -Id 5 -Activity "Scoring OCR variants" -Status "$summaryCounter/$($textFiles.Count): $($textFile.Directory.Name)/$($textFile.Name)" -Current $summaryCounter -Total $textFiles.Count
    if ($textFile.Directory.Name -notmatch "^(?:auto_)?columns(\d+)$") {
        continue
    }
    $isAutoVariant = $textFile.Directory.Name -match "^auto_"
    if ($AutoOnly -and !$isAutoVariant) {
        continue
    }
    $fileColumnCount = [int]$Matches[1]
    if (!$AutoOnly -and !$isAutoVariant -and $ColumnCounts -notcontains $fileColumnCount) {
        continue
    }
    if ($textFile.BaseName -notmatch "^merged\.([^.]+)\.psm(\d+)$") {
        continue
    }
    $fileProfile = $Matches[1]
    $filePsm = [int]$Matches[2]
    if (($SelectedOcrProfiles | ForEach-Object { $_.Name }) -notcontains $fileProfile) {
        continue
    }
    if ($PsmModes -notcontains $filePsm) {
        continue
    }

    $correctedPath = [IO.Path]::Combine(
        [IO.Path]::GetDirectoryName($textFile.FullName),
        ([IO.Path]::GetFileNameWithoutExtension($textFile.FullName) + ".corrected.txt")
    )
    $scorePath = if (!$NoTextCorrection -and (Test-Path -LiteralPath $correctedPath)) { $correctedPath } else { $textFile.FullName }

    $text = Get-Content -LiteralPath $scorePath -Raw -Encoding UTF8
    $score = Get-TextScore -Text $text
    $relative = Resolve-Path -LiteralPath $textFile.FullName -Relative
    $correctedRelative = if (Test-Path -LiteralPath $correctedPath) { (Resolve-Path -LiteralPath $correctedPath -Relative) } else { "" }
    $summary.Add([pscustomobject]@{
        Variant = ($textFile.Directory.Name + "/" + $textFile.BaseName)
        Profile = $fileProfile
        Psm = $filePsm
        Score = $score.Score
        Lines = $score.Lines
        Cyrillic = $score.Cyrillic
        ArticleWords = $score.ArticleWords
        LeaderLines = $score.LeaderLines
        LongLines = $score.LongLines
        TextFile = $relative
        CorrectedTextFile = $correctedRelative
    })
}
Complete-StepProgress -Id 5 -Activity "Scoring OCR variants"
Write-ProgressLog "OCR scoring complete: $($summary.Count) candidate variant(s)."

$summaryPath = Join-Path $pageOutDir "summary.tsv"
$summary |
    Sort-Object -Property @{ Expression = "Score"; Descending = $true }, Variant |
    Export-Csv -LiteralPath $summaryPath -Delimiter "`t" -NoTypeInformation -Encoding UTF8

$summary |
    Sort-Object -Property @{ Expression = "Score"; Descending = $true }, Variant |
    Select-Object -First 20
