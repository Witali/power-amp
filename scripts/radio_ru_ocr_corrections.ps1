$script:RadioRuLookalikeMap = [System.Collections.Generic.Dictionary[string, string]]::new([System.StringComparer]::Ordinal)
foreach ($pair in @(
    @("A", "А"), @("B", "В"), @("C", "С"), @("E", "Е"), @("H", "Н"), @("K", "К"), @("M", "М"), @("O", "О"), @("P", "Р"), @("T", "Т"), @("X", "Х"), @("Y", "У"),
    @("a", "а"), @("c", "с"), @("e", "е"), @("h", "н"), @("k", "к"), @("m", "м"), @("o", "о"), @("p", "р"), @("x", "х"), @("y", "у")
)) {
    $script:RadioRuLookalikeMap.Add($pair[0], $pair[1])
}

function Convert-RadioRuLookalikes {
    param([string]$Text)

    if (!$Text) {
        return $Text
    }

    $cyrillicCount = ([regex]::Matches($Text, "[А-Яа-яЁё]")).Count
    if ($cyrillicCount -eq 0) {
        return $Text
    }

    return [regex]::Replace($Text, "[A-Za-zА-Яа-яЁё]+", {
        param($match)

        $token = $match.Value
        $tokenCyrillicCount = ([regex]::Matches($token, "[А-Яа-яЁё]")).Count
        $tokenLatinCount = ([regex]::Matches($token, "[A-Za-z]")).Count
        $shouldConvert = ($tokenCyrillicCount -gt 0 -and $tokenLatinCount -gt 0) -or ($tokenLatinCount -gt 0 -and $token.Length -eq 1)

        if (!$shouldConvert) {
            return $token
        }

        $builder = [System.Text.StringBuilder]::new()
        foreach ($char in $token.ToCharArray()) {
            $key = [string]$char
            if ($script:RadioRuLookalikeMap.ContainsKey($key)) {
                [void]$builder.Append($script:RadioRuLookalikeMap[$key])
            }
            else {
                [void]$builder.Append($char)
            }
        }

        return $builder.ToString()
    })
}

function Repair-RadioRuOcrLine {
    param([string]$Line)

    if ($null -eq $Line) {
        return $Line
    }

    $line = $Line

    # Direct fixes before converting Latin lookalikes.
    $line = [regex]::Replace($line, "\bYUM\b", "УНЧ", "IgnoreCase")
    $line = [regex]::Replace($line, "\bYH\b", "УНЧ", "IgnoreCase")
    $line = [regex]::Replace($line, "\bHY\b", "НЧ", "IgnoreCase")
    $line = [regex]::Replace($line, "\bHO\b", "НЧ", "IgnoreCase")

    $line = Convert-RadioRuLookalikes -Text $line

    $literalReplacements = [ordered]@{
        "Рации" = "Радио"
        "Рално" = "Радио"
        "Радно" = "Радио"
        "Раливо" = "Радио"
        "Рийио" = "Радио"
        "радповещательной" = "радиовещательной"
        "радноприемник" = "радиоприемник"
        "радноприемники" = "радиоприемники"
        "ралноприемник" = "радиоприемник"
        "ралностаиций" = "радиостанций"
        "радиостатций" = "радиостанций"
        "радиостаиций" = "радиостанций"
        "радиовлнаратуры" = "радиоаппаратуры"
        "Магиитофон" = "Магнитофон"
        "магцитофон" = "магнитофон"
        "Олектрофои" = "Электрофон"
        "электрофои" = "электрофон"
        "Плектроииый" = "Электронный"
        "Олентронный" = "Электронный"
        "электроииый" = "электронный"
        "Элентроника" = "Электроника"
        "элентронные" = "электронные"
        "звуиовой" = "звуковой"
        "звукоиой" = "звуковой"
        "Звуновосироизводящее" = "Звуковоспроизводящее"
        "сопропождения" = "сопровождения"
        "бестраноформаторных" = "бестрансформаторных"
        "бестрансформатовных" = "бестрансформаторных"
        "бестралеформаторный" = "бестрансформаторный"
        "стивисформаторный" = "бестрансформаторный"
        "стивисформаторных" = "бестрансформаторных"
        "иепоереретвенней" = "непосредственной"
        "иепоереретвенной" = "непосредственной"
        "универсальиый" = "универсальный"
        "ишерсальиый" = "универсальный"
        "ниоерсальный" = "универсальный"
        "ишерсальный" = "универсальный"
        "зуеплитени" = "усилители"
        "уеплитени" = "усилители"
        "зуплитени" = "усилители"
        "устоитель" = "усилитель"
        "устоителя" = "усилителя"
        "устоители" = "усилители"
        "убилитель" = "усилитель"
        "убилителя" = "усилителя"
        "уснлитель" = "усилитель"
        "усплитель" = "усилитель"
        "успления" = "усиления"
        "Крыло " = "Крылов "
        "Крыло." = "Крылов."
        "Стре." = "Стрельцов."
        "Стрельн" = "Стрельцов"
        "Ввеильсв" = "Васильев"
        "Виеильв" = "Васильев"
        "Василии." = "Васильев."
        "Хиар" = "Хмарцев"
        "Хмарщей" = "Хмарцев"
        "Хморщей" = "Хмарцев"
        "Суупереенеролии" = "супергетеродин"
        "супергетероиии" = "супергетеродин"
        "супергетеролны" = "супергетеродин"
    }

    foreach ($key in $literalReplacements.Keys) {
        $line = $line.Replace($key, $literalReplacements[$key])
    }

    $line = [regex]::Replace($line, "\b(?:РАДИОЛЮБИТЕЛЬСКИЙ|РАДИОЛЮБИТЕЛЬСКИК)\s+КОНСТРУКЦИИ\b", "РАДИОЛЮБИТЕЛЬСКИЕ КОНСТРУКЦИИ")
    $line = [regex]::Replace($line, "\bрадиолюбительски[йк]\s+конструкции\b", "радиолюбительские конструкции", "IgnoreCase")
    $line = [regex]::Replace($line, "\bэлектроакустика[,\.\s]+звуко[а-яё]*", "ЭЛЕКТРОАКУСТИКА, ЗВУКОЗАПИСЬ", "IgnoreCase")

    # Common Russian OCR confusion around amplifier/transistor terms.
    $line = [regex]::Replace($line, "\b(?!резистор)(?:[а-яё]{0,4})зистор(н[а-яё]*)\b", "транзистор`$1", "IgnoreCase")
    $line = [regex]::Replace($line, "\bтра[ий]зистор(н[а-яё]*)\b", "транзистор`$1", "IgnoreCase")
    $line = [regex]::Replace($line, "\bтрипаистор(н[а-яё]*)\b", "транзистор`$1", "IgnoreCase")
    $line = [regex]::Replace($line, "\b(?:[а-яё]{0,4})зистор[иі](ый|ые|ых|ым|ого)\b", "транзисторн`$1", "IgnoreCase")
    $line = [regex]::Replace($line, "\bтра[ий]зист[оу]р[иі](ый|ые|ых|ым|ого)\b", "транзисторн`$1", "IgnoreCase")
    $line = [regex]::Replace($line, "\bтранзистор[ин]{2,}й\b", "транзисторный", "IgnoreCase")
    $line = [regex]::Replace($line, "\bтранзистор[ин]{2,}е\b", "транзисторные", "IgnoreCase")
    $line = [regex]::Replace($line, "\bтранзисториые\b", "транзисторные", "IgnoreCase")

    $line = [regex]::Replace($line, "\bус[нп]лител", "усилител", "IgnoreCase")
    $line = [regex]::Replace($line, "\bуоилител", "усилител", "IgnoreCase")
    $line = [regex]::Replace($line, "\bуз[ие]лител", "усилител", "IgnoreCase")
    $line = [regex]::Replace($line, "\bуснлени", "усилени", "IgnoreCase")
    $line = [regex]::Replace($line, "\bусплени", "усилени", "IgnoreCase")

    # НЧ/УНЧ are very often distorted in old scans.
    $line = [regex]::Replace($line, "(усилител[а-яё]*\s+)(?:ИЧ|НУ|НО|НЦ|НУ|Н0|ИЦ|ШЧ|МЧ)\b", "`${1}НЧ", "IgnoreCase")
    $line = [regex]::Replace($line, "(бестрансформаторн[а-яё]*\s+)(?:УПЧ|УМ|УИЧ|У1Ч|УМЧ)\b", "`${1}УНЧ", "IgnoreCase")
    $line = [regex]::Replace($line, "\bУПЧ\b(?=.*бестрансформаторн)", "УНЧ", "IgnoreCase")

    $line = [regex]::Replace($line, "^\s*ходный усилитель\s+НЧ\b", "Выходной усилитель НЧ", "IgnoreCase")
    $line = [regex]::Replace($line, "\bпрокополосный[""']?\s+усилитель\b", "широкополосный усилитель", "IgnoreCase")
    $line = [regex]::Replace($line, "\b[сc]вяз[ьи]\s+в\s+бестрансформаторн", "связь в бестрансформаторн", "IgnoreCase")

    # Clean up spacing after replacements, but keep line boundaries intact.
    $line = $line -replace "[ \t]{2,}", " "
    $line = $line -replace "\s+([,.;:])", '$1'
    $line = $line.Trim()

    return $line
}

function Repair-RadioRuOcrText {
    param([string]$Text)

    if ($null -eq $Text) {
        return $Text
    }

    $lines = $Text -split "\r?\n"
    $fixed = foreach ($line in $lines) {
        Repair-RadioRuOcrLine -Line $line
    }

    return ($fixed -join "`r`n")
}

function Repair-RadioRuOcrFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InputPath,
        [string]$OutputPath,
        [string]$LogPath
    )

    if (!$OutputPath) {
        $OutputPath = [IO.Path]::Combine(
            [IO.Path]::GetDirectoryName($InputPath),
            ([IO.Path]::GetFileNameWithoutExtension($InputPath) + ".corrected.txt")
        )
    }

    if (!$LogPath) {
        $LogPath = [IO.Path]::Combine(
            [IO.Path]::GetDirectoryName($InputPath),
            ([IO.Path]::GetFileNameWithoutExtension($InputPath) + ".corrections.tsv")
        )
    }

    $raw = Get-Content -LiteralPath $InputPath -Raw -Encoding UTF8
    $rawLines = $raw -split "\r?\n"
    $correctedLines = New-Object System.Collections.Generic.List[string]
    $changes = New-Object System.Collections.Generic.List[object]

    for ($i = 0; $i -lt $rawLines.Count; $i++) {
        $before = $rawLines[$i]
        $after = Repair-RadioRuOcrLine -Line $before
        $correctedLines.Add($after)
        if ($before -ne $after) {
            $changes.Add([pscustomobject]@{
                Line = $i + 1
                Before = $before
                After = $after
            })
        }
    }

    ($correctedLines -join "`r`n") | Set-Content -LiteralPath $OutputPath -Encoding UTF8
    $changes | Export-Csv -LiteralPath $LogPath -Delimiter "`t" -NoTypeInformation -Encoding UTF8

    [pscustomobject]@{
        InputPath = $InputPath
        OutputPath = $OutputPath
        LogPath = $LogPath
        ChangedLines = $changes.Count
    }
}
