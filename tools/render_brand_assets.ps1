param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot),
    [string]$QaOutputPath = '',
    [string]$MasterPath = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$pluginRoot = Join-Path $Root 'plugins'
$manifestFiles = @(Get-ChildItem -LiteralPath $pluginRoot -Recurse -File -Filter 'Logo Generation Manifest 200826.json')
if ($manifestFiles.Count -ne 1) {
    throw "Expected exactly one Logo Generation Manifest 200826.json below $pluginRoot; found $($manifestFiles.Count)."
}

$manifestPath = $manifestFiles[0].FullName
$assetDir = Split-Path -Parent $manifestPath
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json

foreach ($required in @('canonical_master', 'master_sha256', 'master_width', 'master_height', 'source_type', 'source_background_policy', 'generation_mode', 'local_edit_status', 'source_crop', 'render_config')) {
    if (-not $manifest.PSObject.Properties.Name.Contains($required)) {
        throw "Logo generation manifest is missing '$required'."
    }
}
if ($manifest.source_type -notin @('original_browser_download', 'operator_supplied_visualization_png')) {
    throw "Unsupported canonical logo source type '$($manifest.source_type)'."
}
if ($manifest.local_edit_status -ne 'none') {
    throw "Canonical logo source declares a local edit and cannot be packaged."
}

if (-not $MasterPath) {
    $MasterPath = Join-Path $Root ([string]$manifest.canonical_master)
} elseif (-not [System.IO.Path]::IsPathRooted($MasterPath)) {
    $MasterPath = Join-Path $Root $MasterPath
}
if (-not (Test-Path -LiteralPath $MasterPath -PathType Leaf)) {
    throw "Missing canonical GPT Image 2 master: $MasterPath"
}

$actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $MasterPath).Hash.ToLowerInvariant()
$expectedHash = ([string]$manifest.master_sha256).ToLowerInvariant()
if ($actualHash -ne $expectedHash) {
    throw "Canonical master hash mismatch. Expected $expectedHash; got $actualHash."
}

$master = [System.Drawing.Bitmap]::FromFile((Resolve-Path -LiteralPath $MasterPath))
try {
    if ($master.Width -ne [int]$manifest.master_width -or $master.Height -ne [int]$manifest.master_height) {
        throw "Canonical master dimensions do not match the manifest."
    }
    if ($master.Width -ne $master.Height) {
        throw "Canonical master must be square."
    }
    if ($manifest.source_background_policy -eq 'transparent_source') {
        if ($master.PixelFormat.ToString() -notmatch 'Argb') {
            throw "Transparent canonical master must retain an alpha channel."
        }
        $cornerAlpha = @(
            $master.GetPixel(0, 0).A,
            $master.GetPixel($master.Width - 1, 0).A,
            $master.GetPixel(0, $master.Height - 1).A,
            $master.GetPixel($master.Width - 1, $master.Height - 1).A
        )
        if (@($cornerAlpha | Where-Object { $_ -ne 0 }).Count -gt 0) {
            throw "Transparent canonical master must have transparent corners; got $($cornerAlpha -join ',')."
        }
    } elseif ($manifest.source_background_policy -ne 'preserve_opaque_source') {
        throw "Unsupported source background policy '$($manifest.source_background_policy)'."
    }

    $crop = $manifest.source_crop
    foreach ($requiredCropField in @('x', 'y', 'width', 'height')) {
        if (-not $crop.PSObject.Properties.Name.Contains($requiredCropField)) {
            throw "Logo source crop is missing '$requiredCropField'."
        }
    }
    if ([int]$crop.width -ne [int]$crop.height) {
        throw "Logo source crop must be square to preserve aspect ratio."
    }
    if ([int]$crop.x -lt 0 -or [int]$crop.y -lt 0 -or [int]$crop.width -le 0 -or [int]$crop.height -le 0) {
        throw "Logo source crop has invalid bounds."
    }
    if (([int]$crop.x + [int]$crop.width) -gt $master.Width -or ([int]$crop.y + [int]$crop.height) -gt $master.Height) {
        throw "Logo source crop exceeds the immutable master bounds."
    }
    $sourceRect = [System.Drawing.Rectangle]::new([int]$crop.x, [int]$crop.y, [int]$crop.width, [int]$crop.height)

    $cfg = $manifest.render_config

    function New-Canvas([int]$Width, [int]$Height, [string]$Background) {
        $bitmap = [System.Drawing.Bitmap]::new($Width, $Height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
        if ($Background -eq 'transparent') {
            $graphics.Clear([System.Drawing.Color]::Transparent)
        } else {
            $graphics.Clear([System.Drawing.ColorTranslator]::FromHtml($Background))
        }
        return @($bitmap, $graphics)
    }

    function Save-Png([System.Drawing.Bitmap]$Bitmap, [string]$Path) {
        $Bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    }

    function Place-Master(
        [System.Drawing.Graphics]$Graphics,
        [System.Drawing.Image]$Master,
        [int]$X,
        [int]$Y,
        [int]$Size
    ) {
        $destination = [System.Drawing.Rectangle]::new($X, $Y, $Size, $Size)
        $Graphics.DrawImage($Master, $destination, $sourceRect, [System.Drawing.GraphicsUnit]::Pixel)
    }

    function Write-Text(
        [System.Drawing.Graphics]$Graphics,
        [string]$Text,
        [float]$X,
        [float]$Y,
        [float]$Size,
        [string]$Color,
        [bool]$Mono = $false,
        [bool]$Bold = $false
    ) {
        $family = if ($Mono) { 'Consolas' } else { 'Segoe UI' }
        $style = if ($Bold) { [System.Drawing.FontStyle]::Bold } else { [System.Drawing.FontStyle]::Regular }
        $font = [System.Drawing.Font]::new($family, $Size, $style, [System.Drawing.GraphicsUnit]::Pixel)
        $brush = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml($Color))
        try { $Graphics.DrawString($Text, $font, $brush, $X, $Y) }
        finally { $font.Dispose(); $brush.Dispose() }
    }

    # Composer icon: a deterministic resize of the immutable selected master.
    $iconBackground = if ($manifest.source_background_policy -eq 'preserve_opaque_source') {
        [string]$cfg.light_background
    } else {
        'transparent'
    }
    $canvas = New-Canvas 512 512 $iconBackground
    try {
        Place-Master $canvas[1] $master 0 0 512
        Save-Png $canvas[0] (Join-Path $assetDir 'icon.png')
    } finally { $canvas[1].Dispose(); $canvas[0].Dispose() }

    # Light and dark product surfaces place the same master without recoloring it.
    foreach ($variant in @(
        @{ Name = 'logo.png'; Background = [string]$cfg.light_background },
        @{ Name = 'logo-dark.png'; Background = [string]$cfg.dark_background }
    )) {
        $canvas = New-Canvas 1024 1024 $variant.Background
        try {
            Place-Master $canvas[1] $master 96 96 832
            Save-Png $canvas[0] (Join-Path $assetDir $variant.Name)
        } finally { $canvas[1].Dispose(); $canvas[0].Dispose() }
    }

    # Repository screenshot. Layout and text are derivative packaging; the logo pixels come only from the master.
    $canvas = New-Canvas 1600 900 ([string]$cfg.dark_background)
    try {
        $g = $canvas[1]
        Place-Master $g $master 62 42 168
        Write-Text $g ([string]$cfg.product_name) 255 66 48 ([string]$cfg.light_text) $false $true
        Write-Text $g ([string]$cfg.tagline) 258 130 25 ([string]$cfg.accent)
        $cardBrush = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml([string]$cfg.card_background))
        try { $g.FillRectangle($cardBrush, 80, 240, 1440, 580) }
        finally { $cardBrush.Dispose() }
        Write-Text $g ([string]$cfg.panel_heading) 128 282 23 ([string]$cfg.secondary) $true $true
        Write-Text $g ([string]$cfg.body) 128 332 24 ([string]$cfg.light_text)
        $lineY = 408
        foreach ($line in @($cfg.panel_lines)) {
            Write-Text $g ([string]$line) 128 $lineY 22 ([string]$cfg.accent) $true
            $lineY += 66
        }
        Write-Text $g 'SOURCE  OPERATOR-SELECTED PNG  |  DERIVATIVES  HASH-VERIFIED' 128 758 18 ([string]$cfg.secondary) $true $true
        Save-Png $canvas[0] (Join-Path $assetDir 'screenshot1.png')
    } finally { $canvas[1].Dispose(); $canvas[0].Dispose() }

    # GitHub social preview uses the same unmodified source at a larger placement.
    $canvas = New-Canvas 1600 900 ([string]$cfg.light_background)
    try {
        $g = $canvas[1]
        Place-Master $g $master 60 150 520
        Write-Text $g ([string]$cfg.product_name) 650 202 62 ([string]$cfg.dark_text) $false $true
        Write-Text $g ([string]$cfg.tagline) 654 292 31 ([string]$cfg.accent)
        Write-Text $g ([string]$cfg.body) 654 354 24 ([string]$cfg.dark_text)
        $cardBrush = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml([string]$cfg.card_background))
        try { $g.FillRectangle($cardBrush, 650, 490, 790, 178) }
        finally { $cardBrush.Dispose() }
        Write-Text $g ([string]$cfg.panel_heading) 696 525 21 ([string]$cfg.secondary) $true $true
        Write-Text $g ([string]@($cfg.panel_lines)[0]) 696 580 22 ([string]$cfg.light_text) $true
        Save-Png $canvas[0] (Join-Path $assetDir 'social-preview.png')
    } finally { $canvas[1].Dispose(); $canvas[0].Dispose() }

    if ($QaOutputPath) {
        if (-not [System.IO.Path]::IsPathRooted($QaOutputPath)) { $QaOutputPath = Join-Path $Root $QaOutputPath }
        [System.IO.Directory]::CreateDirectory((Split-Path -Parent $QaOutputPath)) | Out-Null
        $canvas = New-Canvas 1100 390 ([string]$cfg.light_background)
        try {
            $g = $canvas[1]
            Write-Text $g "$($cfg.product_name) actual-size source QA" 36 20 30 ([string]$cfg.dark_text) $false $true
            $x = 36
            foreach ($size in @(16, 24, 32, 64, 128)) {
                $lightBrush = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml([string]$cfg.light_background))
                $darkBrush = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml([string]$cfg.dark_background))
                try {
                    $g.FillRectangle($lightBrush, $x, 80, 180, 112)
                    $g.FillRectangle($darkBrush, $x, 205, 180, 112)
                } finally { $lightBrush.Dispose(); $darkBrush.Dispose() }
                $imageX = $x + [int]((180 - $size) / 2)
                Place-Master $g $master $imageX (80 + [int]((112 - $size) / 2)) $size
                Place-Master $g $master $imageX (205 + [int]((112 - $size) / 2)) $size
                Write-Text $g "$size px" ($x + 56) 330 18 ([string]$cfg.dark_text) $true $true
                $x += 208
            }
            Save-Png $canvas[0] $QaOutputPath
        } finally { $canvas[1].Dispose(); $canvas[0].Dispose() }
    }

    $outputs = @('icon.png', 'logo.png', 'logo-dark.png', 'screenshot1.png', 'social-preview.png') | ForEach-Object {
        $path = Join-Path $assetDir $_
        [ordered]@{ path = $path; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant() }
    }
    [ordered]@{
        status = 'ok'
        source_policy = 'immutable_operator_selected_master_only'
        master_path = (Resolve-Path -LiteralPath $MasterPath).Path
        master_sha256 = $actualHash
        outputs = $outputs
    } | ConvertTo-Json -Depth 5
}
finally {
    $master.Dispose()
}
