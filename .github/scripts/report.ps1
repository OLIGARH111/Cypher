. "$PSScriptRoot/capture.ps1"
$form=New-Object Windows.Forms.Form
$form.Text='Cypher Voice 2.0 - actual Windows test results'
$form.ClientSize=New-Object Drawing.Size 1000,650
$form.StartPosition='CenterScreen'
$box=New-Object Windows.Forms.TextBox
$box.Multiline=$true;$box.ReadOnly=$true;$box.Dock='Fill';$box.ScrollBars='Vertical'
$box.Font=New-Object Drawing.Font 'Consolas',13
$lines=Get-Content screenshots/verification.txt | Where-Object {$_ -match 'ACOUSTIC|PASS:|Ran |OK$'}
$box.Text="WINDOWS TEST SESSION - CYPHER 1.1.1`r`n`r`n"+($lines -join "`r`n")+"`r`n`r`nSynthetic speech fixtures. This is a test report, not the Cypher settings screen."
$form.Controls.Add($box)
$form.Show()
[Windows.Forms.Application]::DoEvents()
Save-Window $form.Handle '03-voice-verification'
$form.Close()
