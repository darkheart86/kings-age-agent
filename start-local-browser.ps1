param(
    [Parameter(Mandatory=$true)][string]$GameUrl,
    [Parameter(Mandatory=$true)][string]$VmTarget,
    [Parameter(Mandatory=$true)][string]$VmFingerprint
)
# Execute no PowerShell do Windows que alcança a VM privada.
# Confirme o fingerprint SSH por canal independente antes de prosseguir.
# Mantenha esta janela aberta enquanto o agente precisar do navegador.
$ErrorActionPreference = 'Stop'
if ($GameUrl -cnotmatch '^https://s[0-9]+-[a-z]{2}\.kingsage\.gameforge\.com/\?village=[0-9]+$') {
    throw 'GameUrl deve ser HTTPS do mundo KingsAge com village numérico.'
}
if ($VmTarget -cnotmatch '^[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+$') {
    throw 'VmTarget deve ser usuario@host da VM.'
}
if ($VmFingerprint -cnotmatch '^SHA256:[A-Za-z0-9+/]{43}$') {
    throw 'VmFingerprint deve ser uma impressão digital SHA256 SSH válida.'
}

$chromeCandidates = @(
    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "${env:LOCALAPPDATA}\Google\Chrome\Application\chrome.exe"
)
$chrome = $chromeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $chrome) { throw 'Chrome não encontrado. Informe onde está chrome.exe.' }
if (-not (Get-Command ssh.exe -ErrorAction SilentlyContinue)) {
    throw 'Cliente OpenSSH do Windows não encontrado. Ative-o antes de continuar.'
}

$profile = Join-Path $env:LOCALAPPDATA 'KingsAge-Agent\Chrome-Profile'
New-Item -ItemType Directory -Force -Path $profile | Out-Null
$game = $GameUrl
$chromeArgs = @(
    '--remote-debugging-address=127.0.0.1',
    '--remote-debugging-port=9222',
    "--user-data-dir=`"$profile`"",
    '--no-first-run',
    $game
)
Start-Process -FilePath $chrome -ArgumentList $chromeArgs

$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $probe = Invoke-RestMethod 'http://127.0.0.1:9222/json/version' -TimeoutSec 1
        if ($probe.Browser -like 'Chrome/*') { $ready = $true; break }
    } catch { Start-Sleep -Milliseconds 500 }
}
if (-not $ready) { throw 'Chrome iniciou, mas a porta local 9222 não respondeu. Verifique se o perfil separado abriu.' }

Write-Host 'Chrome separado pronto. Faça login na janela do KingsAge; não digite senhas no chat.'
Write-Host 'O SSH pedirá confirmação da chave da VM e talvez sua senha SSH (não a senha do jogo).'
Write-Host "Confirme a chave ED25519 somente se o fingerprint for: $VmFingerprint"
Write-Host 'Esta janela deve permanecer aberta. Ctrl+C encerra somente o túnel.'
& ssh.exe -N -T -R '127.0.0.1:9224:127.0.0.1:9222' -o 'ExitOnForwardFailure=yes' -o 'StrictHostKeyChecking=ask' -o 'ServerAliveInterval=30' -o 'ServerAliveCountMax=3' $VmTarget
if ($LASTEXITCODE -ne 0) { throw "Túnel SSH falhou (código $LASTEXITCODE)." }
