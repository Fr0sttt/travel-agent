param(
    [string]$HostName = "",
    [int]$Port = 0,
    [string]$User = "",
    [string]$RemoteRoot = "",
    [ValidateSet("auto", "backend", "middleware", "system", "health")]
    [string]$Mode = "auto",
    [int]$Lines = 200,
    [switch]$NoFollow
)

# 从 backend 目录转发到项目根目录的真实脚本，方便 PyCharm/终端直接运行。
$scriptDir = $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($scriptDir) -and $MyInvocation.MyCommand.Path) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
if ([string]::IsNullOrWhiteSpace($scriptDir)) {
    $scriptDir = Join-Path -Path (Get-Location).Path -ChildPath "scripts"
}

$rootScriptPath = Join-Path -Path $scriptDir -ChildPath "..\..\..\scripts\watch-server-logs.ps1"
$resolvedRootScript = Resolve-Path -LiteralPath $rootScriptPath -ErrorAction SilentlyContinue
if (-not $resolvedRootScript) {
    throw "找不到根目录日志脚本，请确认项目根目录下存在 scripts\watch-server-logs.ps1。当前脚本目录: $scriptDir"
}
$rootScript = $resolvedRootScript.ProviderPath

$forwardArgs = @{
    HostName = $HostName
    Port = $Port
    User = $User
    RemoteRoot = $RemoteRoot
    Mode = $Mode
    Lines = $Lines
}

if ($NoFollow) {
    $forwardArgs.NoFollow = $true
}

& $rootScript @forwardArgs
