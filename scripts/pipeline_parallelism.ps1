function Get-PipelinePositiveInt {
    param(
        [object]$Value,
        [int]$Fallback
    )

    try {
        $parsed = [int]$Value
    }
    catch {
        return $Fallback
    }
    if ($parsed -gt 0) {
        return $parsed
    }
    return $Fallback
}

function Get-PipelineParallelismConfig {
    param([string]$ProjectRoot)

    $path = Join-Path $ProjectRoot "config\pipeline_parallelism.json"
    $defaults = [pscustomobject]@{
        MaxParallelOcrTasks = 1
        TesseractThreadsPerProcess = 1
    }
    if (!(Test-Path -LiteralPath $path)) {
        return $defaults
    }

    $raw = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    [pscustomobject]@{
        MaxParallelOcrTasks = Get-PipelinePositiveInt -Value $raw.max_parallel_ocr_tasks -Fallback $defaults.MaxParallelOcrTasks
        TesseractThreadsPerProcess = Get-PipelinePositiveInt -Value $raw.tesseract_threads_per_process -Fallback $defaults.TesseractThreadsPerProcess
    }
}
