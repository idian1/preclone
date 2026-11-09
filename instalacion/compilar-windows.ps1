$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
$compilador = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$fuente = Join-Path $PSScriptRoot 'InstalarPreclone.cs'
$salida = Join-Path $raiz 'Instalar-Preclone.exe'

& $compilador /nologo /codepage:65001 /target:exe /platform:x64 /optimize+ /reference:System.IO.Compression.FileSystem.dll /reference:System.IO.Compression.dll "/out:$salida" $fuente
if ($LASTEXITCODE -ne 0) {
    throw 'No se pudo compilar el instalador.'
}
