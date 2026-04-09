Add-Type -AssemblyName System.Drawing

$outputPath = Join-Path $PSScriptRoot "..\services\agent\tests\fixtures\scenario_2_account_screenshot.png"
$outputPath = [System.IO.Path]::GetFullPath($outputPath)

$width = 1440
$height = 900

$bitmap = [System.Drawing.Bitmap]::new($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit

function New-ColorBrush {
    param(
        [int]$R,
        [int]$G,
        [int]$B,
        [int]$A = 255
    )
    return [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb($A, $R, $G, $B))
}

function Draw-RoundedRect {
    param(
        [System.Drawing.Graphics]$Graphics,
        [System.Drawing.RectangleF]$Rect,
        [float]$Radius,
        [System.Drawing.Brush]$Fill,
        [System.Drawing.Pen]$Pen
    )

    $diameter = $Radius * 2
    $path = [System.Drawing.Drawing2D.GraphicsPath]::new()
    $path.AddArc($Rect.X, $Rect.Y, $diameter, $diameter, 180, 90)
    $path.AddArc($Rect.Right - $diameter, $Rect.Y, $diameter, $diameter, 270, 90)
    $path.AddArc($Rect.Right - $diameter, $Rect.Bottom - $diameter, $diameter, $diameter, 0, 90)
    $path.AddArc($Rect.X, $Rect.Bottom - $diameter, $diameter, $diameter, 90, 90)
    $path.CloseFigure()
    $Graphics.FillPath($Fill, $path)
    if ($Pen) {
        $Graphics.DrawPath($Pen, $path)
    }
    $path.Dispose()
}

function Draw-Label {
    param(
        [string]$Text,
        [System.Drawing.Font]$Font,
        [System.Drawing.Brush]$Brush,
        [float]$X,
        [float]$Y
    )
    $graphics.DrawString($Text, $Font, $Brush, $X, $Y)
}

$bgRect = [System.Drawing.Rectangle]::new(0, 0, $width, $height)
$bgBrush = [System.Drawing.Drawing2D.LinearGradientBrush]::new(
    [System.Drawing.Point]::new(0, 0),
    [System.Drawing.Point]::new($width, $height),
    [System.Drawing.Color]::FromArgb(247, 251, 255),
    [System.Drawing.Color]::FromArgb(229, 238, 250)
)
$graphics.FillRectangle($bgBrush, $bgRect)

$blueGlow = New-ColorBrush 37 99 235 28
$graphics.FillEllipse($blueGlow, -80, -60, 420, 260)
$graphics.FillEllipse($blueGlow, 1080, 620, 360, 240)

$panelBrush = New-ColorBrush 255 255 255 232
$panelPen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(20, 15, 23, 42), 1)

$sidebarRect = [System.Drawing.RectangleF]::new(52, 44, 280, 808)
$mainTopRect = [System.Drawing.RectangleF]::new(354, 44, 1034, 258)
$bannerRect = [System.Drawing.RectangleF]::new(354, 320, 1034, 118)
$mainBottomRect = [System.Drawing.RectangleF]::new(354, 456, 1034, 396)

Draw-RoundedRect -Graphics $graphics -Rect $sidebarRect -Radius 24 -Fill $panelBrush -Pen $panelPen
Draw-RoundedRect -Graphics $graphics -Rect $mainTopRect -Radius 24 -Fill $panelBrush -Pen $panelPen
Draw-RoundedRect -Graphics $graphics -Rect $bannerRect -Radius 24 -Fill ([System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(245, 234, 194))) -Pen $panelPen
Draw-RoundedRect -Graphics $graphics -Rect $mainBottomRect -Radius 24 -Fill $panelBrush -Pen $panelPen

$brandBadgeBrush = [System.Drawing.Drawing2D.LinearGradientBrush]::new(
    [System.Drawing.Point]::new(78, 74),
    [System.Drawing.Point]::new(120, 116),
    [System.Drawing.Color]::FromArgb(15, 23, 42),
    [System.Drawing.Color]::FromArgb(37, 99, 235)
)
Draw-RoundedRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(78, 76, 42, 42)) -Radius 14 -Fill $brandBadgeBrush -Pen $null

$fontTitle = [System.Drawing.Font]::new("Georgia", 24, [System.Drawing.FontStyle]::Bold)
$fontLarge = [System.Drawing.Font]::new("Georgia", 30, [System.Drawing.FontStyle]::Bold)
$fontBody = [System.Drawing.Font]::new("Segoe UI", 15, [System.Drawing.FontStyle]::Regular)
$fontBodyBold = [System.Drawing.Font]::new("Segoe UI", 15, [System.Drawing.FontStyle]::Bold)
$fontSmall = [System.Drawing.Font]::new("Segoe UI", 13, [System.Drawing.FontStyle]::Regular)
$fontSmallBold = [System.Drawing.Font]::new("Segoe UI", 12, [System.Drawing.FontStyle]::Bold)
$fontMetric = [System.Drawing.Font]::new("Georgia", 30, [System.Drawing.FontStyle]::Bold)
$fontMetricLabel = [System.Drawing.Font]::new("Segoe UI", 12, [System.Drawing.FontStyle]::Regular)
$fontChip = [System.Drawing.Font]::new("Segoe UI", 11, [System.Drawing.FontStyle]::Bold)

$textBrush = New-ColorBrush 15 23 42
$mutedBrush = New-ColorBrush 100 116 139
$accentBrush = New-ColorBrush 37 99 235
$greenBrush = New-ColorBrush 22 101 52
$amberBrush = New-ColorBrush 154 103 0
$whiteBrush = New-ColorBrush 255 255 255

Draw-Label "Upstream Shop" $fontTitle $textBrush 134 78
Draw-Label "Customer account portal" $fontSmall $mutedBrush 136 110

$navItems = @(
    @{ Text = "Profile"; Active = $false },
    @{ Text = "Order history"; Active = $true },
    @{ Text = "Payments"; Active = $false },
    @{ Text = "Saved cards"; Active = $false },
    @{ Text = "Support inbox"; Active = $false }
)

$navY = 164
foreach ($item in $navItems) {
    $fill = if ($item.Active) {
        [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(225, 236, 255))
    } else {
        [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(245, 248, 252))
    }
    $pen = if ($item.Active) {
        [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(80, 37, 99, 235), 1)
    } else {
        [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(0, 0, 0, 0), 1)
    }
    Draw-RoundedRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(72, $navY, 238, 48)) -Radius 14 -Fill $fill -Pen $pen
    $brush = if ($item.Active) { $textBrush } else { $mutedBrush }
    $font = if ($item.Active) { $fontBodyBold } else { $fontBody }
    Draw-Label $item.Text $font $brush 92 ($navY + 12)
    $navY += 58
}

Draw-Label "Last successful card charge: Visa ending 8842" $fontSmall $mutedBrush 74 796

Draw-Label "Recent orders still waiting for" $fontLarge $textBrush 388 68
Draw-Label "payment confirmation" $fontLarge $textBrush 388 110
Draw-Label "Customers report they already paid, but the account screen still shows the orders as pending." $fontBody $mutedBrush 390 166
Draw-Label "No refund or cancellation entries are visible in the account timeline." $fontBody $mutedBrush 390 192

Draw-RoundedRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(1130, 86, 220, 42)) -Radius 20 -Fill ([System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(255, 247, 214))) -Pen $null
Draw-Label "Pending state visible to customers" $fontChip $amberBrush 1152 99

$metricXs = @(390, 720, 1035)
$metricLabels = @("ORDERS SHOWN", "MARKED PAID BY BANK", "STILL PENDING IN ACCOUNT")
$metricValues = @("4", "4", "4")
for ($i = 0; $i -lt 3; $i++) {
    Draw-Label $metricLabels[$i] $fontMetricLabel $mutedBrush $metricXs[$i] 222
    Draw-Label $metricValues[$i] $fontMetric $textBrush $metricXs[$i] 244
}

Draw-Label "Payment completed, but the order history never advanced." ([System.Drawing.Font]::new("Georgia", 22, [System.Drawing.FontStyle]::Bold)) $amberBrush 388 346
Draw-Label "The bank confirmation email arrived 18 minutes ago for all four orders." $fontBody $textBrush 390 384
Draw-Label "The UI below still shows Pending payment and no shipment workflow has started." $fontBody $textBrush 390 408
Draw-RoundedRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(1176, 360, 164, 36)) -Radius 18 -Fill ([System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(220, 252, 231))) -Pen $null
Draw-Label "Card charged successfully" $fontChip $greenBrush 1196 370

$headers = @("ORDER", "CHARGED AMOUNT", "BANK STATE", "ORDER STATE", "UPDATED")
$headerXs = @(394, 692, 870, 1044, 1222)
for ($i = 0; $i -lt $headers.Length; $i++) {
    Draw-Label $headers[$i] $fontMetricLabel $mutedBrush $headerXs[$i] 492
}

$rows = @(
    @{Order="Order #99821"; Subtitle="Wireless earbuds - 2 items"; Amount='$84.99'; Updated="18 min ago"; Hint="Timeline mismatch: settlement recorded by bank, but downstream order state did not change."},
    @{Order="Order #99822"; Subtitle="Kitchen mixer - 1 item"; Amount='$129.00'; Updated="16 min ago"; Hint="Customer-visible contradiction: charge confirmed, order still not released for fulfillment."},
    @{Order="Order #99823"; Subtitle="Standing desk lamp - 3 items"; Amount='$56.40'; Updated="14 min ago"; Hint="No manual review flag is present. The order simply never advanced after payment."},
    @{Order="Order #99824"; Subtitle="Travel backpack - 1 item"; Amount='$73.15'; Updated="11 min ago"; Hint="Useful visual clue for scenario 2: the UI is stale even though payment completed upstream."}
)

$rowY = 526
foreach ($row in $rows) {
    Draw-RoundedRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(380, $rowY, 982, 74)) -Radius 18 -Fill ([System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(252, 253, 255))) -Pen ([System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(18, 15, 23, 42), 1))
    Draw-Label $row.Order ([System.Drawing.Font]::new("Georgia", 18, [System.Drawing.FontStyle]::Bold)) $textBrush 404 ($rowY + 12)
    Draw-Label $row.Subtitle $fontSmall $mutedBrush 404 ($rowY + 40)
    Draw-Label $row.Amount ([System.Drawing.Font]::new("Georgia", 18, [System.Drawing.FontStyle]::Bold)) $textBrush 700 ($rowY + 22)

    Draw-RoundedRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(850, $rowY + 18, 142, 28)) -Radius 14 -Fill ([System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(220, 252, 231))) -Pen $null
    Draw-Label "Payment succeeded" ([System.Drawing.Font]::new("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)) $greenBrush 871 ($rowY + 24)

    Draw-RoundedRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(1032, $rowY + 18, 136, 28)) -Radius 14 -Fill ([System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(255, 247, 214))) -Pen $null
    Draw-Label "Pending payment" ([System.Drawing.Font]::new("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)) $amberBrush 1051 ($rowY + 24)

    Draw-Label $row.Updated $fontSmall $textBrush 1240 ($rowY + 24)
    Draw-Label $row.Hint ([System.Drawing.Font]::new("Segoe UI", 11, [System.Drawing.FontStyle]::Regular)) $mutedBrush 402 ($rowY + 78)
    $rowY += 92
}

$bitmap.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)

$graphics.Dispose()
$bitmap.Dispose()
$bgBrush.Dispose()
$brandBadgeBrush.Dispose()
$panelBrush.Dispose()
$panelPen.Dispose()
$blueGlow.Dispose()
$fontTitle.Dispose()
$fontLarge.Dispose()
$fontBody.Dispose()
$fontBodyBold.Dispose()
$fontSmall.Dispose()
$fontSmallBold.Dispose()
$fontMetric.Dispose()
$fontMetricLabel.Dispose()
$fontChip.Dispose()
$textBrush.Dispose()
$mutedBrush.Dispose()
$accentBrush.Dispose()
$greenBrush.Dispose()
$amberBrush.Dispose()
$whiteBrush.Dispose()

Write-Host "Generated $outputPath"
