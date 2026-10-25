param([string]$ArtifactDir, [string]$Tag, [string]$Browser)
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path $ArtifactDir).Path
$scratch = Join-Path ([IO.Path]::GetTempPath()) ('waterfox-negative-' + [guid]::NewGuid())
New-Item -ItemType Directory $scratch | Out-Null
Get-ChildItem $source -File | Copy-Item -Destination $scratch
function Assert-Rejected([string]$Expected) {
  try {
    & "$PSScriptRoot/verify-package.ps1" -ArtifactDir $scratch -Tag $Tag -Browser $Browser -CandidateSha ('a' * 40) -ProofDir (Join-Path $scratch 'proof')
  } catch {
    if ($_.Exception.Message -notlike "*$Expected*") { throw }
    Write-Output "PASS: rejected $Expected"
    return
  }
  throw "Verification unexpectedly accepted: $Expected"
}
$manifest = Join-Path $scratch 'checksums.txt'
$originalManifest = Get-Content $manifest -Raw
# A changed artifact must fail before extraction or execution.
$installer = Join-Path $scratch "WaterfoxSetup-$Browser.exe"
$stream = [IO.File]::OpenWrite($installer)
$stream.WriteByte(0)
$stream.Close()
Assert-Rejected 'Checksum mismatch'
Copy-Item (Join-Path $source "WaterfoxSetup-$Browser.exe") $installer -Force
Add-Content $manifest ($originalManifest.Split("`n")[0])
Assert-Rejected 'Checksum mismatch or duplicate'
Set-Content $manifest $originalManifest.TrimEnd()
# Rehashing a substituted executable must not bypass publisher verification.
Copy-Item "$env:WINDIR/System32/notepad.exe" $installer -Force
$digest = (Get-FileHash $installer).Hash.ToLowerInvariant()
$modifiedManifest = [regex]::Replace($originalManifest, '(?m)^[a-f0-9]{64}  WaterfoxSetup-[^\r\n]+', "$digest  WaterfoxSetup-$Browser.exe")
Set-Content $manifest $modifiedManifest.TrimEnd()
Assert-Rejected 'Invalid BrowserWorks signature'
