param([switch]$SelfTest, [switch]$Demo, [switch]$ScanSelfTest)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Core = Join-Path $Here 'sprite_turntable.py'
$Blender = $null
$Finished = $false
$Proc = $null
$LogFile = $null
$OutDir = $null
$ScanProc = $null
$ScanLog = $null
$ScanId = [System.Diagnostics.Process]::GetCurrentProcess().Id
$LastScan = $null
$ScanOut = Join-Path $env:TEMP ('sprite_scan_out_' + [System.Diagnostics.Process]::GetCurrentProcess().Id)
$Total = 0
$Done = 0

function Find-Blender {
    if ($env:BLENDER_EXE -and (Test-Path $env:BLENDER_EXE)) { return $env:BLENDER_EXE }
    $candidates = @(
        'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe',
        'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe',
        'C:\Program Files\Blender Foundation\Blender 5.0\blender.exe',
        'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe',
        'C:\Program Files\Blender Foundation\Blender 4.4\blender.exe',
        'C:\Program Files\Blender Foundation\Blender 4.3\blender.exe',
        'C:\Program Files\Blender Foundation\Blender 4.2\blender.exe',
        'C:\Program Files\Blender Foundation\Blender 4.0\blender.exe',
        'C:\Program Files\Blender Foundation\Blender 3.6\blender.exe'
    )
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    $cmd = Get-Command blender -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Read-Shared($path) {
    try {
        $fs = [System.IO.File]::Open($path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        $sr = New-Object System.IO.StreamReader($fs)
        $text = $sr.ReadToEnd()
        $sr.Close()
        return $text
    } catch {
        return ''
    }
}
function Start-ActionScan {
    $model = $ModelBox.Text.Trim()
    if (-not (Test-Path $model)) { return }
    $blender = Find-Blender
    if (-not $blender) {
        $AnimHint.Text = 'Blender was not found, so the animations cannot be read.'
        return
    }
    if ($script:ScanProc) {
        try { $script:ScanProc.Kill() } catch { }
        $script:ScanProc = $null
    }
    $q = [char]34
    $argline = '--background --factory-startup --python ' + $q + $Core + $q + ' -- --model ' + $q + $model + $q + ' --out ' + $q + $script:ScanOut + $q + ' --list-actions'
    $script:ScanLog = Join-Path $env:TEMP ('sprite_scan_' + $script:ScanId + '.log')
    $env:PYTHONUNBUFFERED = '1'
    $script:ScanProc = Start-Process -FilePath $blender -ArgumentList $argline -RedirectStandardOutput $script:ScanLog -RedirectStandardError ($script:ScanLog + '.err') -NoNewWindow -PassThru
    $script:LastScan = $model
    $AnimHint.Text = 'Reading the animations in the model...'
    $Timer.Start()
}

function Read-Actions {
    if (-not $script:ScanLog -or -not (Test-Path $script:ScanLog)) { return }
    $text = Read-Shared $script:ScanLog
    if (-not $text) { return }
    $m = [regex]::Match($text, 'ACTIONS_JSON:(.*)')
    if (-not $m.Success) {
        $AnimHint.Text = 'No animations were found in that model.'
        return
    }
    try { $items = $m.Groups[1].Value.Trim() | ConvertFrom-Json } catch { $items = @() }
    $AnimBox.Items.Clear()
    $AnimBox.Items.Add('(rest pose - no animation)')
    $count = 0
    foreach ($a in $items) {
        if ($a.bones -gt 0) { $AnimBox.Items.Add($a.name); $count = $count + 1 }
    }
    if ($count -gt 1) { $AnimBox.Items.Add('ALL animations') }
    $AnimBox.SelectedIndex = 0
    if ($count -gt 0) {
        $AnimHint.Text = 'Found ' + $count + ' animation(s). Pick one, or ALL animations.'
        $FramesBox.Text = 'all'
    } else {
        $AnimHint.Text = 'That model has no animations. The rest pose will be shot.'
    }
}

$form = New-Object System.Windows.Forms.Form
$form.Text = 'Sprite Turntable - make a sprite sheet'
$form.ClientSize = New-Object System.Drawing.Size(620, 664)
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.BackColor = [System.Drawing.Color]::FromArgb(28, 30, 34)
$form.ForeColor = [System.Drawing.Color]::White

function New-Label($x, $y, $w, $h, $text, $size) {
    $l = New-Object System.Windows.Forms.Label
    $l.Location = New-Object System.Drawing.Point($x, $y)
    $l.Size = New-Object System.Drawing.Size($w, $h)
    $l.Text = $text
    $l.ForeColor = [System.Drawing.Color]::Gainsboro
    if ($size) { $l.Font = New-Object System.Drawing.Font('Segoe UI', $size, [System.Drawing.FontStyle]::Bold) }
    return $l
}

function New-Button($x, $y, $w, $h, $text) {
    $b = New-Object System.Windows.Forms.Button
    $b.Location = New-Object System.Drawing.Point($x, $y)
    $b.Size = New-Object System.Drawing.Size($w, $h)
    $b.Text = $text
    $b.FlatStyle = 'Flat'
    $b.BackColor = [System.Drawing.Color]::FromArgb(52, 120, 200)
    $b.ForeColor = [System.Drawing.Color]::White
    return $b
}

$title = New-Label 20 16 580 32 'Sprite Turntable' 16
$form.Controls.Add($title)
$form.Controls.Add((New-Label 20 52 580 22 'Turn a 3D model into a flat sprite sheet. Everything stays on this computer.'))
$form.Controls.Add((New-Label 20 88 580 22 '1. Your model  (.glb, .gltf, .fbx or .blend)'))
$ModelBox = New-Object System.Windows.Forms.TextBox
$ModelBox.Location = New-Object System.Drawing.Point(20, 112)
$ModelBox.Size = New-Object System.Drawing.Size(470, 26)
$ModelBox.BackColor = [System.Drawing.Color]::FromArgb(45, 48, 54)
$ModelBox.ForeColor = [System.Drawing.Color]::White
$form.Controls.Add($ModelBox)
$ModelBtn = New-Button 500 111 100 28 'BROWSE'
$form.Controls.Add($ModelBtn)
$form.Controls.Add((New-Label 20 152 580 22 '2. Where to save the frames'))
$OutBox = New-Object System.Windows.Forms.TextBox
$OutBox.Location = New-Object System.Drawing.Point(20, 176)
$OutBox.Size = New-Object System.Drawing.Size(470, 26)
$OutBox.BackColor = [System.Drawing.Color]::FromArgb(45, 48, 54)
$OutBox.ForeColor = [System.Drawing.Color]::White
$form.Controls.Add($OutBox)
$OutBtn = New-Button 500 175 100 28 'BROWSE'
$form.Controls.Add($OutBtn)
$form.Controls.Add((New-Label 20 216 140 22 '3. How many angles'))
$opt16 = New-Object System.Windows.Forms.RadioButton
$opt16.Text = '16'
$opt16.Location = New-Object System.Drawing.Point(165, 211)
$opt16.ForeColor = [System.Drawing.Color]::White
$opt16.AutoSize = $true
$form.Controls.Add($opt16)
$opt32 = New-Object System.Windows.Forms.RadioButton
$opt32.Text = '32'
$opt32.Location = New-Object System.Drawing.Point(212, 211)
$opt32.ForeColor = [System.Drawing.Color]::White
$opt32.AutoSize = $true
$form.Controls.Add($opt32)
$opt64 = New-Object System.Windows.Forms.RadioButton
$opt64.Text = '64'
$opt64.Location = New-Object System.Drawing.Point(259, 211)
$opt64.Checked = $true
$opt64.ForeColor = [System.Drawing.Color]::White
$opt64.AutoSize = $true
$form.Controls.Add($opt64)
$form.Controls.Add((New-Label 300 216 120 22 '4. Frame size'))
$opt256 = New-Object System.Windows.Forms.RadioButton
$opt256.Text = '256'
$opt256.Location = New-Object System.Drawing.Point(430, 211)
$opt256.ForeColor = [System.Drawing.Color]::White
$opt256.AutoSize = $true
$form.Controls.Add($opt256)
$opt512 = New-Object System.Windows.Forms.RadioButton
$opt512.Text = '512'
$opt512.Location = New-Object System.Drawing.Point(482, 211)
$opt512.Checked = $true
$opt512.ForeColor = [System.Drawing.Color]::White
$opt512.AutoSize = $true
$form.Controls.Add($opt512)
$opt1024 = New-Object System.Windows.Forms.RadioButton
$opt1024.Text = '1024'
$opt1024.Location = New-Object System.Drawing.Point(534, 211)
$opt1024.ForeColor = [System.Drawing.Color]::White
$opt1024.AutoSize = $true
$form.Controls.Add($opt1024)
$form.Controls.Add((New-Label 20 250 300 22 '5. Animation'))
$AnimBox = New-Object System.Windows.Forms.ComboBox
$AnimBox.Location = New-Object System.Drawing.Point(20, 274)
$AnimBox.Size = New-Object System.Drawing.Size(300, 26)
$AnimBox.DropDownStyle = 'DropDownList'
$AnimBox.BackColor = [System.Drawing.Color]::FromArgb(45, 48, 54)
$AnimBox.ForeColor = [System.Drawing.Color]::White
$AnimBox.Items.Add('(rest pose - no animation)')
$AnimBox.SelectedIndex = 0
$form.Controls.Add($AnimBox)
$ScanBtn = New-Button 328 273 88 28 'SCAN'
$ScanBtn.BackColor = [System.Drawing.Color]::FromArgb(70, 74, 82)
$form.Controls.Add($ScanBtn)
$AnimHint = New-Label 20 302 580 22 'Pick a model and the animations in it are listed here.'
$form.Controls.Add($AnimHint)
$form.Controls.Add((New-Label 20 326 80 22 'Frames'))
$FramesBox = New-Object System.Windows.Forms.TextBox
$FramesBox.Location = New-Object System.Drawing.Point(96, 322)
$FramesBox.Size = New-Object System.Drawing.Size(90, 26)
$FramesBox.BackColor = [System.Drawing.Color]::FromArgb(45, 48, 54)
$FramesBox.ForeColor = [System.Drawing.Color]::White
$FramesBox.Text = 'all'
$form.Controls.Add($FramesBox)
$form.Controls.Add((New-Label 196 326 380 22 'all = the whole cycle, or 1,8,16 for chosen frames'))

$ViewBtn = New-Button 232 482 200 34 'VIEW THE SHEET'
$ViewBtn.Enabled = $false
$ViewBtn.BackColor = [System.Drawing.Color]::FromArgb(70, 74, 82)
$form.Controls.Add($ViewBtn)

$MakeBtn = New-Object System.Windows.Forms.Button
$MakeBtn.Location = New-Object System.Drawing.Point(20, 336)
$MakeBtn.Size = New-Object System.Drawing.Size(580, 62)
$MakeBtn.Text = 'MAKE SPRITE SHEET'
$MakeBtn.FlatStyle = 'Flat'
$MakeBtn.BackColor = [System.Drawing.Color]::FromArgb(38, 160, 90)
$MakeBtn.ForeColor = [System.Drawing.Color]::White
$MakeBtn.Font = New-Object System.Drawing.Font('Segoe UI', 16, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($MakeBtn)
$Bar = New-Object System.Windows.Forms.ProgressBar
$Bar.Location = New-Object System.Drawing.Point(20, 414)
$Bar.Size = New-Object System.Drawing.Size(580, 24)
$form.Controls.Add($Bar)
$Status = New-Label 20 446 580 24 ''
$form.Controls.Add($Status)
$OpenBtn = New-Button 20 482 200 34 'OPEN THE FOLDER'
$OpenBtn.Enabled = $false
$OpenBtn.BackColor = [System.Drawing.Color]::FromArgb(70, 74, 82)
$form.Controls.Add($OpenBtn)
$form.Controls.Add((New-Label 20 530 580 44 'Needs Blender (free): https://www.blender.org/download/  No account, no cloud, no network.'))

$ModelBtn.Add_Click({
    $dlg = New-Object System.Windows.Forms.OpenFileDialog
    $dlg.Title = 'Pick your model'
    $dlg.Filter = '3D models (*.glb;*.gltf;*.fbx;*.blend)|*.glb;*.gltf;*.fbx;*.blend|All files (*.*)|*.*'
    if ($dlg.ShowDialog() -eq 'OK') {
        $ModelBox.Text = $dlg.FileName
        Start-ActionScan
        if (-not $OutBox.Text) {
            $OutBox.Text = Join-Path (Split-Path -Parent $dlg.FileName) 'sprite_sheet'
        }
    }
})

$OutBtn.Add_Click({
    $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
    $dlg.Description = 'Where should the frames go'
    if ($dlg.ShowDialog() -eq 'OK') { $OutBox.Text = $dlg.SelectedPath }
})

$OpenBtn.Add_Click({
    if ($OutDir -and (Test-Path $OutDir)) { Start-Process explorer.exe -ArgumentList $OutDir }
})

$ScanBtn.Add_Click({ Start-ActionScan })

$ModelBox.Add_TextChanged({
    $model = $ModelBox.Text.Trim()
    if (-not $model) { return }
    if (-not (Test-Path $model)) { return }
    if ($model -eq $script:LastScan) { return }
    $script:LastScan = $model
    Start-ActionScan
})

$ViewBtn.Add_Click({
    $viewer = Join-Path $script:OutDir 'sprite_viewer.html'
    if ($script:OutDir -and (Test-Path $viewer)) { Start-Process $viewer }
    else { [System.Windows.Forms.MessageBox]::Show('Make the sheet first. The player is written next to the frames.') | Out-Null }
})

$OnMake = {
    $model = $ModelBox.Text.Trim()
    if (-not (Test-Path $model)) {
        [System.Windows.Forms.MessageBox]::Show('Pick your model first.') | Out-Null
        return
    }
    $out = $OutBox.Text.Trim()
    if (-not $out) { $out = Join-Path (Split-Path -Parent $model) 'sprite_sheet' }
    if (-not (Test-Path $out)) { New-Item -ItemType Directory -Force -Path $out | Out-Null }
    $blender = Find-Blender
    if (-not $blender) {
        [System.Windows.Forms.MessageBox]::Show('Blender was not found. Install it from blender.org, or set BLENDER_EXE to the full path of blender.exe.') | Out-Null
        return
    }
    $angles = '16'
    if ($opt32.Checked) { $angles = '32' }
    if ($opt64.Checked) { $angles = '64' }
    $res = '256'
    if ($opt512.Checked) { $res = '512' }
    if ($opt1024.Checked) { $res = '1024' }
    $script:OutDir = $out
    $script:Total = [int]$angles * $actCount
    $script:Done = 0
    $script:LogFile = Join-Path $out 'sprite_turntable.log'
    $action = $AnimBox.Text
    $frames = $FramesBox.Text.Trim()
    if (-not $frames) { $frames = 'all' }
    $extra = ''
    $q = [char]34
    $actCount = 1
    if ($action -eq 'ALL animations') {
        $extra = ' --action all --frames ' + $frames
        $actCount = [Math]::Max(1, $AnimBox.Items.Count - 2)
    } elseif ($action -and $action -ne '(rest pose - no animation)') {
        $extra = ' --action ' + $q + $action + $q + ' --frames ' + $frames
    }
    $argline = '--background --factory-startup --python "' + $Core + '" -- --model "' + $model + '" --out "' + $out + '" --angles ' + $angles + ' --res ' + $res + ' --prefix sheet' + $extra
    $env:PYTHONUNBUFFERED = '1'
    $script:Proc = Start-Process -FilePath $blender -ArgumentList $argline -RedirectStandardOutput $script:LogFile -RedirectStandardError (Join-Path $out 'sprite_turntable.err.txt') -NoNewWindow -PassThru
    $MakeBtn.Enabled = $false
    $MakeBtn.Text = 'WORKING...'
    $OpenBtn.Enabled = $false
    $Status.Text = 'Rendering ' + $angles + ' angles...'
    $Bar.Value = 0
    $Timer.Start()
}

$MakeBtn.Add_Click($OnMake)

$Timer = New-Object System.Windows.Forms.Timer
$Timer.Interval = 500
$OnTick = {
    if ($script:ScanProc) {
        if ($script:ScanProc.HasExited) {
            $script:ScanProc.WaitForExit()
            $script:ScanProc = $null
            Read-Actions
            if (-not $script:Proc) { $Timer.Stop() }
        }
        return
    }
    if (-not $script:Proc) { $Timer.Stop(); return }
    if (-not $script:Proc.HasExited) {
        if (Test-Path $script:LogFile) {
            $text = Read-Shared $script:LogFile
            if ($text) {
                $hits = ([regex]::Matches($text, '  angle ')).Count
                if ($hits -gt $script:Done) {
                    $script:Done = $hits
                    $Bar.Value = [Math]::Min(100, [int](100 * $hits / $script:Total))
                    $Status.Text = 'Rendering angle ' + $hits + ' of ' + $script:Total
                }
            }
        }
        return
    }
    $Timer.Stop()
    $script:Proc.WaitForExit()
    $code = $script:Proc.ExitCode
    if ($script:LogFile -and (Test-Path $script:LogFile)) {
        $tail = Read-Shared $script:LogFile
        $hits = ([regex]::Matches($tail, '  angle ')).Count
        if ($hits -gt $script:Done) { $script:Done = $hits }
    }
    $script:Proc = $null
    $MakeBtn.Enabled = $true
    $MakeBtn.Text = 'MAKE SPRITE SHEET'
    $ok = ($code -eq 0)
    if (-not $ok -and $script:LogFile -and (Test-Path $script:LogFile)) {
        $tail = Read-Shared $script:LogFile
        if ($tail -match 'SHEET DONE') { $ok = $true }
    }
    if ($ok) {
        $Bar.Value = 100
        $script:Finished = $true
        $Status.Text = 'Done. ' + $script:Done + ' frames in ' + $script:OutDir
        $OpenBtn.Enabled = $true
        $ViewBtn.Enabled = $true
    } else {
        $Status.Text = 'That did not work. The log is in ' + $script:OutDir
        [System.Windows.Forms.MessageBox]::Show('The render failed. Read sprite_turntable.log in the output folder.') | Out-Null
    }
}

$Timer.Add_Tick($OnTick)

if ($Demo) {
    $ModelBox.Text = $env:ST_MODEL
    $OutBox.Text = $env:ST_OUT
    & $OnMake
}
$form.Add_Shown({ $ModelBox.Focus() })
if ($ScanSelfTest) {
    $ModelBox.Text = $env:ST_MODEL
    Start-ActionScan
    while ($script:ScanProc) { Start-Sleep -Milliseconds 500 }
    Read-Actions
    $names = @()
    foreach ($item in $AnimBox.Items) { $names += [string]$item }
    Write-Host ('SCAN SELFTEST count=' + $names.Count + ' items=' + ($names -join '|'))
    if ($names.Count -gt 1) { exit 0 }
    exit 1
}
if ($SelfTest) {
    $ModelBox.Text = $env:ST_MODEL
    $OutBox.Text = $env:ST_OUT
    & $OnMake
    while ($script:Proc) { Start-Sleep -Milliseconds 400; & $OnTick }
    Write-Host ('SELFTEST finished=' + $script:Finished + ' frames=' + $script:Done + ' out=' + $script:OutDir)
    if ($script:Finished) { exit 0 }
    exit 1
}
[void]$form.ShowDialog()