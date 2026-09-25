param(
    [Parameter(Mandatory=$true)][string]$RpmBundle,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [string]$CatalogImage = 'registry.access.redhat.com/ubi8/ubi:8.10',
    [switch]$RefreshFeed,
    [string]$WslDistribution = '',
    [switch]$ReuseFeedCache,
    [string]$FeedCache = "$PSScriptRoot/../work/native-feed/nvd-cache"
)
$ErrorActionPreference = 'Stop'
$bundlePath = (Resolve-Path -LiteralPath $RpmBundle).Path
if ($RefreshFeed) {
    $feedArgs = @("$PSScriptRoot/refresh-feed.py", '--cache-dir', $FeedCache)
    if ($ReuseFeedCache) { $feedArgs += '--reuse-cache' }
    & python @feedArgs
    if ($LASTEXITCODE -ne 0) { throw 'Feed refresh has gaps; inspect its query errors before packaging.' }
}
$modulePath = $PSScriptRoot
if ($WslDistribution) {
    $bundlePath = & wsl -d $WslDistribution -- wslpath -a $bundlePath.Replace('\', '/')
    if ($LASTEXITCODE -ne 0) { throw 'WSL bundle path conversion failed' }
    $bundlePath = $bundlePath.Trim()
    $modulePath = & wsl -d $WslDistribution -- wslpath -a $modulePath.Replace('\', '/')
    if ($LASTEXITCODE -ne 0) { throw 'WSL module path conversion failed' }
    $modulePath = $modulePath.Trim()
}
$containerArgs = @('run', '--rm', '--network=none', '--cap-drop=ALL', '--security-opt=no-new-privileges',
    '-v', "${bundlePath}:/bundle:ro", '-v', "${modulePath}:/module", '--entrypoint', '/usr/libexec/platform-python',
    $CatalogImage, '/module/build-catalog.py', '/bundle', '--output', '/module/catalog.json')
if ($WslDistribution) { & wsl -d $WslDistribution -- podman @containerArgs }
else { & podman @containerArgs }
if ($LASTEXITCODE -ne 0) { throw 'Catalogue generation failed' }
$previousOS = $env:GOOS
$previousArch = $env:GOARCH
Push-Location $PSScriptRoot
try {
    Remove-Item Env:GOOS,Env:GOARCH -ErrorAction SilentlyContinue
    & python -m unittest test_feed.py test_report.py
    if ($LASTEXITCODE -ne 0) { throw 'Feed tests failed' }
    & go test ./...
    if ($LASTEXITCODE -ne 0) { throw 'Module tests failed' }
    $env:GOOS='wasip1'; $env:GOARCH='wasm'
    & go build -trimpath '-ldflags=-s -w' -buildmode=c-shared -o modules/linuxoss-artifact-evidence.wasm .
    if ($LASTEXITCODE -ne 0) { throw 'WASM build failed' }
    & python package-bundle.py --output-dir $OutputDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Packaging failed' }
} finally {
    $env:GOOS=$previousOS
    $env:GOARCH=$previousArch
    Pop-Location
}
