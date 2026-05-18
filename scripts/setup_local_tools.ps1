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

$Root = Split-Path -Parent $PSScriptRoot
$Tools = Join-Path $Root "local_tools"
$Downloads = Join-Path $Tools "downloads"
$NodeCache = Join-Path $Root "node_cache"
$PythonPackages = Join-Path $Tools "python_packages"
$LayoutPythonPackages = @("opencv-python-headless", "numpy", "pillow")

$SevenZipPackage = "7zip.portable.nupkg"
$SevenZipPackageUrl = "https://community.chocolatey.org/api/v2/package/7zip.portable"
$SevenZipExtracted = Join-Path $Tools "7zip-portable"

$NodeVersion = "20.11.1"
$NodeArchive = "node-v$NodeVersion-win-x64.zip"
$NodeUrl = "https://nodejs.org/dist/v$NodeVersion/$NodeArchive"
$NodeExtracted = Join-Path $Tools "node"
$LocalNodeRoot = Join-Path $NodeExtracted "node-v$NodeVersion-win-x64"
$LocalNodeExe = Join-Path $LocalNodeRoot "node.exe"

$NgspiceVersion = "46"
$NgspiceArchive = "ngspice-46_64.7z"
$NgspiceUrl = "https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/$NgspiceVersion/$NgspiceArchive"
$NgspiceExe = Join-Path $Tools "ngspice\Spice64\bin\ngspice_con.exe"

$GoVersion = "1.26.3"
$GoArchive = "go$GoVersion.windows-amd64.zip"
$GoUrl = "https://go.dev/dl/$GoArchive"
$GoExtracted = Join-Path $Tools "go"
$GoExe = Join-Path $GoExtracted "bin\go.exe"

$TesseractVersion = "5.5.0.20241111"
$TesseractPackage = "tesseract.$TesseractVersion.nupkg"
$TesseractPackageUrl = "https://community.chocolatey.org/api/v2/package/tesseract/$TesseractVersion"
$TesseractExtracted = Join-Path $Tools "Tesseract-extracted"
$TesseractExe = Join-Path $TesseractExtracted "tesseract.exe"
$TessData = Join-Path $TesseractExtracted "tessdata"

$HunspellVersion = "1.7.0"
$HunspellPackage = "hunspell.portable.$HunspellVersion.nupkg"
$HunspellPackageUrl = "https://community.chocolatey.org/api/v2/package/hunspell.portable/$HunspellVersion"
$HunspellBinaryZip = "hunspell-msvc-Release-x64.zip"
$HunspellBinaryUrl = "https://github.com/mlt/hunspell/releases/download/appveyor_v1.7.0/$HunspellBinaryZip"
$HunspellExtracted = Join-Path $Tools "hunspell"
$HunspellDictDir = Join-Path $Tools "hunspell-dictionaries"
$HunspellDictionaryUrls = @{
    "ru_RU.aff" = "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/ru_RU/ru_RU.aff"
    "ru_RU.dic" = "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/ru_RU/ru_RU.dic"
    "en_US.aff" = "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/en/en_US.aff"
    "en_US.dic" = "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/en/en_US.dic"
}

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Ensure-Directory {
    param([string]$Path)
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

function Expand-ZipPackage {
    param(
        [string]$Archive,
        [string]$Destination
    )

    Ensure-Directory $Destination
    $zip = $Archive
    $copiedZip = $null
    if ([System.IO.Path]::GetExtension($Archive) -ne ".zip") {
        $copiedZip = Join-Path $Downloads ([System.IO.Path]::GetFileNameWithoutExtension($Archive) + ".zip")
        Copy-Item -LiteralPath $Archive -Destination $copiedZip -Force
        $zip = $copiedZip
    }

    Expand-Archive -LiteralPath $zip -DestinationPath $Destination -Force
}

function Install-Local7Zip {
    Write-Host "7-Zip was not found. Downloading a local portable copy."
    $nupkg = Join-Path $Downloads $SevenZipPackage
    Invoke-Download -Uri $SevenZipPackageUrl -OutFile $nupkg

    if ($Force -and (Test-Path -LiteralPath $SevenZipExtracted)) {
        Remove-Item -LiteralPath $SevenZipExtracted -Recurse -Force
    }
    Expand-ZipPackage -Archive $nupkg -Destination $SevenZipExtracted

    $exe = Get-ChildItem -Path $SevenZipExtracted -Recurse -Filter "7z.exe" |
        Select-Object -First 1
    if (!$exe) {
        throw "7z.exe was not found after extracting $nupkg"
    }

    return $exe.FullName
}

function Find-7Zip {
    if ($SevenZipPath -and (Test-Path -LiteralPath $SevenZipPath)) {
        return (Resolve-Path -LiteralPath $SevenZipPath).Path
    }

    $cmd = Get-Command 7z.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd) {
        return $cmd.Source
    }

    $candidates = @(
        "C:\Program Files\7-Zip\7z.exe",
        "C:\Program Files (x86)\7-Zip\7z.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    return Install-Local7Zip
}

function Invoke-Download {
    param(
        [string]$Uri,
        [string]$OutFile,
        [switch]$Overwrite
    )

    if ((Test-Path -LiteralPath $OutFile) -and !$Force -and !$Overwrite) {
        Write-Host "Using cached file: $OutFile"
        return
    }

    Ensure-Directory (Split-Path -Parent $OutFile)
    Write-Host "Downloading $Uri"
    Invoke-WebRequest -Uri $Uri -OutFile $OutFile -MaximumRedirection 10 -UserAgent "Mozilla/5.0"
}

function Test-Archive {
    param(
        [string]$SevenZip,
        [string]$Archive
    )

    & $SevenZip t $Archive | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Resolve-SourceForgeHtmlDownload {
    param([string]$Path)

    $text = Get-Content -LiteralPath $Path -Raw -ErrorAction SilentlyContinue
    if (!$text -or ($text -notmatch "<html")) {
        return $null
    }

    $match = [regex]::Match($text, 'url=([^"'']+)')
    if (!$match.Success) {
        return $null
    }

    return [System.Net.WebUtility]::HtmlDecode($match.Groups[1].Value)
}

function Install-Ngspice {
    param([string]$SevenZip)

    Write-Step "Checking ngspice"
    if ((Test-Path -LiteralPath $NgspiceExe) -and !$Force) {
        & $NgspiceExe -v
        return
    }

    $archive = Join-Path $Downloads $NgspiceArchive
    Invoke-Download -Uri $NgspiceUrl -OutFile $archive

    if (!(Test-Archive -SevenZip $SevenZip -Archive $archive)) {
        $direct = Resolve-SourceForgeHtmlDownload -Path $archive
        if (!$direct) {
            throw "Downloaded ngspice file is not a 7z archive and no SourceForge redirect was found."
        }
        Write-Host "Following SourceForge mirror URL."
        Invoke-Download -Uri $direct -OutFile $archive -Overwrite
    }

    if (!(Test-Archive -SevenZip $SevenZip -Archive $archive)) {
        throw "Downloaded ngspice archive is invalid: $archive"
    }

    $target = Join-Path $Tools "ngspice"
    if ($Force -and (Test-Path -LiteralPath $target)) {
        Remove-Item -LiteralPath $target -Recurse -Force
    }
    Ensure-Directory $target
    & $SevenZip x -y "-o$target" $archive | Out-Null
    if (!(Test-Path -LiteralPath $NgspiceExe)) {
        throw "ngspice_con.exe was not found after extraction: $NgspiceExe"
    }
    & $NgspiceExe -v
}

function Install-Tesseract {
    param([string]$SevenZip)

    Write-Step "Checking Tesseract OCR"
    if (!(Test-Path -LiteralPath $TesseractExe) -or $Force) {
        $nupkg = Join-Path $Downloads $TesseractPackage
        $nupkgDir = Join-Path $Downloads "tesseract-nupkg"
        Invoke-Download -Uri $TesseractPackageUrl -OutFile $nupkg

        if ($Force -and (Test-Path -LiteralPath $nupkgDir)) {
            Remove-Item -LiteralPath $nupkgDir -Recurse -Force
        }
        Ensure-Directory $nupkgDir
        & $SevenZip x -y "-o$nupkgDir" $nupkg | Out-Null

        $installer = Get-ChildItem -Path $nupkgDir -Recurse -Filter "tesseract-ocr-w64-setup-*.exe" |
            Select-Object -First 1
        if (!$installer) {
            throw "Could not find tesseract Windows installer inside $nupkg"
        }

        if ($Force -and (Test-Path -LiteralPath $TesseractExtracted)) {
            Remove-Item -LiteralPath $TesseractExtracted -Recurse -Force
        }
        Ensure-Directory $TesseractExtracted
        & $SevenZip x -y "-o$TesseractExtracted" $installer.FullName | Out-Null

        if (!(Test-Path -LiteralPath $TesseractExe)) {
            throw "tesseract.exe was not found after extraction: $TesseractExe"
        }
    }

    Ensure-Directory $TessData
    $langs = @{
        "rus.traineddata" = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/rus.traineddata"
        "eng.traineddata" = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata"
        "osd.traineddata" = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/osd.traineddata"
    }

    foreach ($name in $langs.Keys) {
        Invoke-Download -Uri $langs[$name] -OutFile (Join-Path $TessData $name)
    }

    & $TesseractExe --tessdata-dir $TessData --list-langs
}

function Install-Go {
    Write-Step "Checking Go"
    if ((Test-Path -LiteralPath $GoExe) -and !$Force) {
        & $GoExe version
        return
    }

    $archive = Join-Path $Downloads $GoArchive
    Invoke-Download -Uri $GoUrl -OutFile $archive

    if ($Force -and (Test-Path -LiteralPath $GoExtracted)) {
        Remove-Item -LiteralPath $GoExtracted -Recurse -Force
    }
    Expand-ZipPackage -Archive $archive -Destination $Tools

    if (!(Test-Path -LiteralPath $GoExe)) {
        throw "go.exe was not found after extracting $archive"
    }
    & $GoExe version
}

function Find-LocalHunspell {
    if (!(Test-Path -LiteralPath $HunspellExtracted)) {
        return $null
    }

    $exe = Get-ChildItem -Path $HunspellExtracted -Recurse -Filter "hunspell.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($exe) {
        return $exe.FullName
    }

    return $null
}

function Find-Hunspell {
    $local = Find-LocalHunspell
    if ($local) {
        return $local
    }

    $cmd = Get-Command hunspell.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd) {
        return $cmd.Source
    }

    return $null
}

function Test-HunspellDictionaries {
    return (
        (Test-Path -LiteralPath (Join-Path $HunspellDictDir "ru_RU.aff")) -and
        (Test-Path -LiteralPath (Join-Path $HunspellDictDir "ru_RU.dic")) -and
        (Test-Path -LiteralPath (Join-Path $HunspellDictDir "en_US.aff")) -and
        (Test-Path -LiteralPath (Join-Path $HunspellDictDir "en_US.dic"))
    )
}

function Confirm-HunspellInstall {
    if ($InstallHunspell) {
        return $true
    }

    if (![Environment]::UserInteractive) {
        return $false
    }

    Write-Host ""
    Write-Host "Hunspell can improve OCR text spell checking for Russian radio articles."
    Write-Host "Install a local portable Hunspell plus ru_RU/en_US dictionaries under local_tools/?"
    $answer = Read-Host "Install Hunspell now? [y/N]"
    return ($answer -match "^(y|yes|д|да)$")
}

function Install-Hunspell {
    param([string]$SevenZip)

    Write-Step "Installing Hunspell spell checker"
    $nupkg = Join-Path $Downloads $HunspellPackage
    Invoke-Download -Uri $HunspellPackageUrl -OutFile $nupkg

    if ($Force -and (Test-Path -LiteralPath $HunspellExtracted)) {
        Remove-Item -LiteralPath $HunspellExtracted -Recurse -Force
    }
    Ensure-Directory $HunspellExtracted
    & $SevenZip x -y "-o$HunspellExtracted" $nupkg | Out-Null

    $hunspell = Find-LocalHunspell
    if (!$hunspell) {
        $binaryZip = Join-Path $Downloads $HunspellBinaryZip
        Invoke-Download -Uri $HunspellBinaryUrl -OutFile $binaryZip
        & $SevenZip x -y "-o$HunspellExtracted" $binaryZip | Out-Null
        $hunspell = Find-LocalHunspell
    }

    if (!$hunspell) {
        throw "hunspell.exe was not found after extracting $nupkg"
    }

    Ensure-Directory $HunspellDictDir
    foreach ($name in $HunspellDictionaryUrls.Keys) {
        Invoke-Download -Uri $HunspellDictionaryUrls[$name] -OutFile (Join-Path $HunspellDictDir $name)
    }

    & $hunspell --version
}

function Ensure-Hunspell {
    param([string]$SevenZip)

    Write-Step "Checking Hunspell spell checker"
    $hunspell = Find-Hunspell
    $hasDictionaries = Test-HunspellDictionaries
    if ($hunspell -and $hasDictionaries -and !$Force) {
        Write-Host "Hunspell: $hunspell"
        Write-Host "Dictionaries: $HunspellDictDir"
        return
    }

    if (Confirm-HunspellInstall) {
        Install-Hunspell -SevenZip $SevenZip
        return
    }

    if ($hunspell) {
        Write-Host "Hunspell found, but local ru_RU dictionaries are missing: $hunspell"
    }
    else {
        Write-Host "Hunspell not installed. Spellcheck will use OCR heuristics until Hunspell is available."
    }
    Write-Host "Run '.\init.ps1 -InstallHunspell' to install it later."
}

function Find-Node {
    if (Test-Path -LiteralPath $LocalNodeExe) {
        return $LocalNodeExe
    }

    $cmd = Get-Command node.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd) {
        return $cmd.Source
    }

    Write-Host "Node.js was not found. Downloading a local Node.js $NodeVersion copy."
    $archive = Join-Path $Downloads $NodeArchive
    Invoke-Download -Uri $NodeUrl -OutFile $archive

    if ($Force -and (Test-Path -LiteralPath $NodeExtracted)) {
        Remove-Item -LiteralPath $NodeExtracted -Recurse -Force
    }
    Expand-ZipPackage -Archive $archive -Destination $NodeExtracted

    if (!(Test-Path -LiteralPath $LocalNodeExe)) {
        throw "node.exe was not found after extracting $archive"
    }
    return $LocalNodeExe
}

function Find-NpmCli {
    param([string]$NodeExe)

    $nodeRoot = Split-Path -Parent $NodeExe
    $candidates = @(
        (Join-Path $nodeRoot "node_modules\npm\bin\npm-cli.js"),
        "C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js",
        "C:\Program Files (x86)\nodejs\node_modules\npm\bin\npm-cli.js"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    throw "npm-cli.js was not found under the Node.js install directory: $nodeRoot"
}

function Install-NodeDependencies {
    Write-Step "Checking Node dependencies"
    if (!(Test-Path -LiteralPath (Join-Path $Root "package.json"))) {
        Write-Host "No package.json found. Skipping npm install."
        return
    }

    $node = Find-Node
    $npmCli = Find-NpmCli -NodeExe $node
    Ensure-Directory $NodeCache

    $packageLock = Join-Path $Root "package-lock.json"
    $npmCommand = if (Test-Path -LiteralPath $packageLock) { "ci" } else { "install" }
    $npmArgs = @($npmCommand, "--cache", $NodeCache, "--prefix", $Root, "--no-audit", "--no-fund")
    & $node $npmCli @npmArgs
    if ($LASTEXITCODE -ne 0) {
        throw "npm $npmCommand failed with exit code $LASTEXITCODE"
    }
}

function Test-LocalPythonPackage {
    param([string]$PackageName)

    if (!(Test-Path -LiteralPath $PythonPackages)) {
        return $false
    }

    $oldPythonPath = $env:PYTHONPATH
    try {
        $env:PYTHONPATH = if ($oldPythonPath) { "$PythonPackages;$oldPythonPath" } else { $PythonPackages }
        & python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('$PackageName') else 1)"
        return $LASTEXITCODE -eq 0
    }
    finally {
        $env:PYTHONPATH = $oldPythonPath
    }
}

function Install-PythonLayoutDependencies {
    Write-Step "Checking Python OpenCV layout dependencies"

    $missing = @()
    foreach ($packageName in @("cv2", "numpy", "PIL")) {
        if (!(Test-LocalPythonPackage -PackageName $packageName)) {
            $missing += $packageName
        }
    }

    if (!$Force -and $missing.Count -eq 0) {
        Write-Host "Python layout dependencies are already installed in $PythonPackages"
        return
    }

    Ensure-Directory $PythonPackages
    & python -m pip install --target $PythonPackages @LayoutPythonPackages
    if ($LASTEXITCODE -ne 0) {
        throw "pip install for Python layout dependencies failed with exit code $LASTEXITCODE"
    }
}

function Show-Summary {
    Write-Step "Setup summary"
    if (Test-Path -LiteralPath $NgspiceExe) {
        Write-Host "ngspice:   $NgspiceExe"
    }
    if (Test-Path -LiteralPath $TesseractExe) {
        Write-Host "Tesseract: $TesseractExe"
        Write-Host "tessdata:  $TessData"
    }
    $hunspell = Find-Hunspell
    if ($hunspell) {
        Write-Host "Hunspell:  $hunspell"
    }
    if (Test-HunspellDictionaries) {
        Write-Host "Hun dicts: $HunspellDictDir"
    }
    if (Test-Path -LiteralPath (Join-Path $Root "node_modules\@resvg\resvg-js")) {
        Write-Host "Node deps: node_modules installed"
    }
    if (Test-LocalPythonPackage -PackageName "cv2") {
        Write-Host "Layout CV: $PythonPackages"
    }
    if (Test-Path -LiteralPath $GoExe) {
        Write-Host "Go:        $GoExe"
    }
    Write-Host ""
    Write-Host "Local tools are under local_tools/ and are ignored by Git."
}

Ensure-Directory $Tools
Ensure-Directory $Downloads

$sevenZip = Find-7Zip
Write-Host "Using 7-Zip: $sevenZip"

if (!$SkipNgspice) {
    Install-Ngspice -SevenZip $sevenZip
}
if (!$SkipOcr) {
    Install-Tesseract -SevenZip $sevenZip
}
if (!$SkipSpellcheck) {
    Ensure-Hunspell -SevenZip $sevenZip
}
if (!$SkipLayoutCv) {
    Install-PythonLayoutDependencies
}
if (!$SkipGo) {
    Install-Go
}
if (!$SkipNode) {
    Install-NodeDependencies
}

Show-Summary
