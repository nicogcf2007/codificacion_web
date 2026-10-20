[CmdletBinding()]
param(
    [string]$Email,
    [string]$Name = 'Administrador'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root 'backend/venv/Scripts/python.exe'
if (-not (Test-Path $python)) { throw 'Falta el entorno Python del backend.' }
if (-not $Email) { $Email = Read-Host 'Correo del primer administrador' }
if ($Email -notmatch '^[^\s@]+@[^\s@]+\.[^\s@]+$') { throw 'Correo no valido.' }
if (-not $Name.Trim()) { throw 'Nombre no valido.' }
$secret = Read-Host 'Contrasena inicial (12 a 128 caracteres)' -AsSecureString
if ($secret.Length -lt 12 -or $secret.Length -gt 128) {
    $secret.Dispose()
    throw 'La contrasena debe tener entre 12 y 128 caracteres.'
}
$keys = @('CNC_ADMIN_EMAIL', 'CNC_ADMIN_PASSWORD', 'CNC_ADMIN_NAME')
$previous = @{}
foreach ($key in $keys) { $previous[$key] = [Environment]::GetEnvironmentVariable($key, 'Process') }
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try {
    $env:CNC_ADMIN_EMAIL = $Email
    $env:CNC_ADMIN_NAME = $Name
    $env:CNC_ADMIN_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    & $python (Join-Path $PSScriptRoot 'provision-admin.py')
    if ($LASTEXITCODE -ne 0) { throw 'El provisionamiento no se completo.' }
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    $secret.Dispose()
    foreach ($key in $keys) { [Environment]::SetEnvironmentVariable($key, $previous[$key], 'Process') }
}
