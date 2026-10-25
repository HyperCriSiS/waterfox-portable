param(
  [Parameter(Mandatory)][string]$ArtifactDir,
  [Parameter(Mandatory)][string]$Tag,
  [Parameter(Mandatory)][string]$Browser,
  [Parameter(Mandatory)][string]$CandidateSha,
  [Parameter(Mandatory)][string]$ProofDir
)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
if ($Tag -notmatch '^\d+\.\d+\.\d+-\d+$' -or $Browser -notmatch '^\d+\.\d+\.\d+(?:\.\d+)?$' -or $CandidateSha -notmatch '^[a-f0-9]{40}$') { throw 'Invalid verification input' }
$root = (Resolve-Path -LiteralPath $ArtifactDir).Path
$expected = @('checksums.txt', "WaterfoxSetup-$Browser.exe", "waterfox-portable-win64-$Tag-setup.exe", "waterfox-portable-win64-$Tag.7z", 'waterfox-portable-win64.exe')
$actual = @(Get-ChildItem -LiteralPath $root -Force)
if ($actual.Where({ $_.PSIsContainer }).Count -or (Compare-Object ($actual.Name | Sort-Object) ($expected | Sort-Object))) { throw 'Unexpected artifact contents' }
$hashes = @{}
foreach ($name in $expected) { $hashes[$name] = (Get-FileHash (Join-Path $root $name) -Algorithm SHA256).Hash.ToLowerInvariant() }
$listed = @{}
foreach ($line in Get-Content (Join-Path $root 'checksums.txt')) {
  if ($line -notmatch '^([a-f0-9]{64})  ([A-Za-z0-9._-]+)$') { throw 'Invalid checksum entry' }
  $digest, $name = $Matches[1], $Matches[2]
  if ($name -eq 'checksums.txt' -or $listed.ContainsKey($name) -or -not $hashes.ContainsKey($name) -or $hashes[$name] -ne $digest) { throw 'Checksum mismatch or duplicate' }
  $listed[$name] = $digest
}
if ($listed.Count -ne 4) { throw 'Incomplete checksum manifest' }
function Assert-Publisher([string]$Path) {
  $signature = Get-AuthenticodeSignature -LiteralPath $Path
  if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch '(?:^|, )O=BrowserWorks Ltd(?:,|$)') { throw "Invalid BrowserWorks signature: $Path" }
}
$installer = Join-Path $root "WaterfoxSetup-$Browser.exe"
Assert-Publisher $installer
$sevenZip = (Get-Command 7z.exe -ErrorAction Stop).Source
$scratch = Join-Path ([IO.Path]::GetTempPath()) ('waterfox-verify-' + [guid]::NewGuid())
$package = Join-Path $scratch 'portable'
$original = Join-Path $scratch 'official'
& $sevenZip t (Join-Path $root "waterfox-portable-win64-$Tag.7z") | Out-Null
& $sevenZip x (Join-Path $root "waterfox-portable-win64-$Tag.7z") "-o$package" -y | Out-Null
& $sevenZip x $installer "-o$original" -y | Out-Null
$metadata = Get-Content (Join-Path $package 'portapp.json') -Raw | ConvertFrom-Json
if ("$($metadata.version)-$($metadata.release)" -ne $Tag) { throw 'Incorrect packaged version' }
if ((Get-FileHash (Join-Path $package 'waterfox-portable.exe')).Hash.ToLowerInvariant() -ne $hashes['waterfox-portable-win64.exe']) { throw 'Launcher identity mismatch' }
Assert-Publisher (Join-Path $package 'app/waterfox.exe')
# The archive must contain the browser extracted from this signed installer, not another download.
foreach ($file in Get-ChildItem (Join-Path $package 'app') -Recurse -File) {
  $relative = [IO.Path]::GetRelativePath((Join-Path $package 'app'), $file.FullName)
  $source = Join-Path (Join-Path $original 'core') $relative
  if (-not (Test-Path -LiteralPath $source -PathType Leaf) -or (Get-FileHash $file.FullName).Hash -ne (Get-FileHash $source).Hash) { throw "Packaged browser differs from signed installer: $relative" }
}
if (Get-ChildItem (Join-Path $package 'app') -Filter 'maintenanceservice*') { throw 'Maintenance service included' }
Set-Content (Join-Path $package 'waterfox-portable.yml') "app:`n  multiple_instances: true"
function Start-Smoke([string]$Name) {
  $shot = Join-Path $package "$Name.png"
  $process = Start-Process (Join-Path $package 'waterfox-portable.exe') -ArgumentList @('--headless','--no-remote','--screenshot',('"'+$shot+'"'),'about:blank') -WindowStyle Hidden -PassThru
  if (-not $process.WaitForExit(60000)) { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue; throw 'Browser startup timed out' }
  if ($process.ExitCode -ne 0 -or -not (Test-Path $shot)) { throw 'Browser startup failed' }
}
Start-Smoke 'fresh'
$profile = Join-Path $package 'data/profile/default'
if (-not (Test-Path (Join-Path $profile 'prefs.js'))) { throw 'Portable profile missing' }
$sentinel = Join-Path $profile 'automation-preservation.txt'
Set-Content $sentinel 'keep-existing-profile'
# A second launch must preserve an existing profile and a user policy.
Set-Content (Join-Path $package 'data/policies.json') '{"policies":{"DisableTelemetry":true}}'
Start-Smoke 'existing'
if ((Get-Content $sentinel -Raw).Trim() -ne 'keep-existing-profile') { throw 'Existing profile changed' }
$policies = (Get-Content (Join-Path $package 'app/distribution/policies.json') -Raw | ConvertFrom-Json).policies
if ($policies.DisableAppUpdate -eq $true -or $policies.DisableTelemetry -ne $true) { throw 'Update or custom policy regression' }
$prefs = Get-Content (Join-Path $package 'app/portapps.cfg') -Raw
if (-not $prefs.Contains('lockPref("extensions.enabledScopes", 4)') -or -not $prefs.Contains('lockPref("extensions.autoDisableScopes", 3)')) { throw 'Extension policy regression' }
New-Item -ItemType Directory -Force -Path $ProofDir | Out-Null
@{ sha=$CandidateSha; tag=$Tag; browser=$Browser; hashes=$hashes } | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $ProofDir 'verification.json') -Encoding utf8
Write-Output 'PASS: signatures, browser provenance, hashes, archive, fresh/existing profiles, updater and extension policies.'
