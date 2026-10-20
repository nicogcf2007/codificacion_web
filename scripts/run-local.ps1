[CmdletBinding()]
param(
    [ValidateSet('blocked', 'demo', 'openai')]
    [string]$Provider = 'blocked',
    [ValidateRange(1024, 65535)]
    [int]$Port = 8000,
    [switch]$Reload,
    [switch]$BootstrapAdmin,
    [string]$AdminEmail,
    [string]$AdminName = 'Administrador'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root 'backend/venv/Scripts/python.exe'
if (-not (Test-Path $python)) {
    throw 'Falta el entorno de Python. Ejecuta los comandos de instalación del README.'
}
if ($Provider -eq 'openai' -and -not $env:OPENAI_API_KEY) {
    throw 'Falta OPENAI_API_KEY en el entorno del servidor. No se ha iniciado ningún trabajo.'
}
$environmentNames = @('CODING_PROVIDER', 'CNC_ADMIN_EMAIL', 'CNC_ADMIN_PASSWORD', 'CNC_ADMIN_NAME')
$previousEnvironment = @{}
foreach ($name in $environmentNames) {
    $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
$locationPushed = $false
try {
    if ($BootstrapAdmin) {
        if (-not $AdminEmail) { $AdminEmail = Read-Host 'Correo del primer administrador' }
        if ($AdminEmail -notmatch '^[^\s@]+@[^\s@]+\.[^\s@]+$') { throw 'Correo de administrador no valido.' }
        $secret = Read-Host 'Contrasena del primer administrador (minimo 12 caracteres)' -AsSecureString
        if ($secret.Length -lt 12) { $secret.Dispose(); throw 'La contrasena requiere al menos 12 caracteres.' }
        $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
        try {
            $env:CNC_ADMIN_EMAIL = $AdminEmail
            $env:CNC_ADMIN_NAME = $AdminName
            $env:CNC_ADMIN_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
        } finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
            $secret.Dispose()
        }
    }
    $env:CODING_PROVIDER = $Provider
    Push-Location $root
    $locationPushed = $true
    $arguments = @('-m', 'uvicorn', 'main:app', '--app-dir', 'backend', '--host', '127.0.0.1', '--port', "$Port")
    if ($Reload) { $arguments += '--reload' }
    & $python @arguments
    if ($LASTEXITCODE -ne 0) { throw "El backend terminó con código $LASTEXITCODE" }
} finally {
    if ($locationPushed) { Pop-Location }
    foreach ($name in $environmentNames) {
        [Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name], 'Process')
    }
}
