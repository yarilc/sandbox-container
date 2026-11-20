# Logic tests of the shared Windows shim (launcher/windows/core.ps1) and the
# thin PowerShell entry. tools/powershell.sh runs them on PowerShell 7 in a
# container without network. Each case builds nothing on Windows: a fake
# wsl.exe first on PATH records every call with the variables WSLENV lists,
# and answers like WSL. The synthetic checkout uses the fixture profiles, and
# each case names the windows-launcher scenario it covers. Windows PowerShell
# 5.1 itself is checked on a Windows host with tools/windows-validate.ps1.
Set-StrictMode -Version 3
$ErrorActionPreference = 'Stop'

$source = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
# SANDBOX_TEST_TMPDIR, as in the other shared tests: the fake wsl.exe must be executable.
$tempRoot = if ($env:SANDBOX_TEST_TMPDIR) { $env:SANDBOX_TEST_TMPDIR } else { [IO.Path]::GetTempPath() }
$work = Join-Path $tempRoot ('shim-tests-' + [guid]::NewGuid().ToString('N'))
$bin = Join-Path $work 'bin'
$script:Record = Join-Path $work 'record.txt'
$project = Join-Path $work 'my project'
$WinEntry = 'C:\Work\checkout'
# Fixture values come from the fixture profiles, never as literals.
$agentProfile = [IO.File]::ReadAllText((Join-Path $source 'tests/fixtures/agent/profile.json')) | ConvertFrom-Json
$shellProfile = [IO.File]::ReadAllText((Join-Path $source 'tests/fixtures/shell-agent/profile.json')) | ConvertFrom-Json
$Name = $agentProfile.name
$Bootstrap = '.local/lib/' + $Name + '/current/launcher/windows/bootstrap.sh'
$Launch = @('-d', 'podman-machine-default', '-u', 'user', '--exec', '/bin/sh', '-c', ('cd && exec /bin/bash ' + $Bootstrap))

$fakeWsl = @'
#!/bin/sh
# Fake wsl.exe: records each call, then answers like WSL.
encode() { printf '%s' "$1" | base64 | tr -d '\n'; }
{
    printf 'call\n'
    for arg in "$@"; do printf 'arg %s\n' "$(encode "$arg")"; done
    printf 'wslenv %s\n' "$(encode "${WSLENV-}")"
    printf 'utf8 %s\n' "${WSL_UTF8-unset}"
    if [ -n "${WSLENV:-}" ]; then
        old_ifs=$IFS
        IFS=:
        for item in $WSLENV; do
            name=${item%%/*}
            if eval "[ -n \"\${$name+x}\" ]"; then
                eval "value=\${$name}"
                printf 'env %s %s\n' "$name" "$(encode "$value")"
            else
                printf 'unset %s\n' "$name"
            fi
        done
        IFS=$old_ifs
    fi
    printf 'end\n'
} >> "$FAKE_WSL_RECORD"
distros=${FAKE_WSL_DISTROS-podman-machine-default}
if [ "$1" = -l ]; then
    list=$distros
    [ "$2" != --running ] || list=${FAKE_WSL_RUNNING-$distros}
    for distro in $list; do
        if [ "${WSL_UTF8:-}" = 1 ] && [ -z "${FAKE_WSL_UTF16:-}" ]; then
            printf '%s\n' "$distro"
        else
            printf '%s\r\n' "$distro" | iconv -f UTF-8 -t UTF-16LE
        fi
    done
    exit 0
fi
case " $distros " in *" $2 "*) ;; *) echo 'Wsl/Service/WSL_E_DISTRO_NOT_FOUND' >&2; exit 255 ;; esac
case " ${FAKE_WSL_USERS-user} " in *" $4 "*) ;; *) echo 'Wsl/WSL_E_USER_NOT_FOUND' >&2; exit 255 ;; esac
shift 4
[ "$*" != '--exec /bin/true' ] || exit 0
case "$*" in
    '--exec /bin/sh -c cd && test -f '*) exit "${FAKE_WSL_INSTALLED:-0}" ;;
    '--exec /bin/sh -c test -d /run/user/'*) exit "${FAKE_WSL_RUNTIME:-0}" ;;
esac
exit "${FAKE_WSL_EXIT:-0}"
'@

# A synthetic checkout: the real entry and shim with a fixture profile.
function Build-Checkout([string]$Root, [string]$Fixture) {
    $profileFile = Join-Path $source ('tests/fixtures/' + $Fixture + '/profile.json')
    $fixtureProfile = [IO.File]::ReadAllText($profileFile) | ConvertFrom-Json
    $entries = @(Get-ChildItem -LiteralPath $source -Filter '*.ps1' -File)
    if ($entries.Count -ne 1) { throw 'expected exactly one PowerShell entry in the checkout root' }
    foreach ($part in @('launcher/windows', 'agent')) {
        [void](New-Item -ItemType Directory -Force -Path (Join-Path $Root $part))
    }
    Copy-Item -LiteralPath $entries[0].FullName -Destination (Join-Path $Root ($fixtureProfile.name + '.ps1'))
    Copy-Item -LiteralPath (Join-Path $source 'launcher/windows/core.ps1') -Destination (Join-Path $Root 'launcher/windows/core.ps1')
    Copy-Item -LiteralPath $profileFile -Destination (Join-Path $Root 'agent/profile.json')
    foreach ($file in @($fixtureProfile.wrapper, 'launcher/core.sh', 'agent/launcher.sh')) {
        [IO.File]::WriteAllText((Join-Path $Root $file), "#!/usr/bin/env bash`n:`n")
    }
    return (Join-Path $Root ($fixtureProfile.name + '.ps1'))
}

function ConvertFrom-Base64([string]$Value) {
    return [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($Value))
}

function ConvertFrom-Payload([string]$Value) {
    $bytes = [Convert]::FromBase64String($Value)
    $items = New-Object System.Collections.Generic.List[string]
    $start = 0
    for ($i = 0; $i -lt $bytes.Length; $i++) {
        if ($bytes[$i] -eq 0) {
            $items.Add([Text.Encoding]::UTF8.GetString($bytes, $start, $i - $start))
            $start = $i + 1
        }
    }
    return , $items.ToArray()
}

function Get-Call {
    $calls = New-Object System.Collections.Generic.List[object]
    if (-not [IO.File]::Exists($script:Record)) { return , $calls.ToArray() }
    $current = $null
    foreach ($line in [IO.File]::ReadAllLines($script:Record)) {
        $parts = $line.Split(' ', 3)
        switch ($parts[0]) {
            'call' {
                $current = [pscustomobject]@{ Arguments = (New-Object System.Collections.Generic.List[string])
                    Env = @{}; Unset = (New-Object System.Collections.Generic.List[string]); WslEnv = ''; Utf8 = '' }
            }
            'arg' { $current.Arguments.Add((ConvertFrom-Base64 $parts[1])) }
            'wslenv' { $current.WslEnv = ConvertFrom-Base64 $parts[1] }
            'utf8' { $current.Utf8 = $parts[1] }
            'env' { $current.Env[$parts[1]] = ConvertFrom-Base64 $parts[2] }
            'unset' { $current.Unset.Add($parts[1]) }
            'end' { $calls.Add($current) }
        }
    }
    return , $calls.ToArray()
}

# Runs a call of the entry or shim in this process, capturing the console.
function Invoke-Entry([scriptblock]$Call) {
    if ([IO.File]::Exists($script:Record)) { [IO.File]::Delete($script:Record) }
    $out = New-Object System.IO.StringWriter
    $err = New-Object System.IO.StringWriter
    $oldOut = [Console]::Out
    $oldErr = [Console]::Error
    [Console]::SetOut($out)
    [Console]::SetError($err)
    try {
        $null = & $Call
        $code = $LASTEXITCODE
    } finally {
        [Console]::SetOut($oldOut)
        [Console]::SetError($oldErr)
    }
    return [pscustomobject]@{ Code = $code; Out = $out.ToString(); Err = $err.ToString(); Calls = (Get-Call) }
}

function Format-Value($Value) {
    return (ConvertTo-Json -InputObject $Value -Compress -Depth 4)
}

function Assert-Equal($Expected, $Actual, [string]$What) {
    if ((Format-Value $Expected) -cne (Format-Value $Actual)) {
        throw ($What + ': expected ' + (Format-Value $Expected) + ', got ' + (Format-Value $Actual))
    }
}

function Assert-True([bool]$Condition, [string]$What) {
    if (-not $Condition) { throw $What }
}

function Assert-Text([string]$Expected, [string]$Text, [string]$What) {
    if (-not $Text.Contains($Expected)) { throw ($What + ': ' + (Format-Value $Expected) + ' not in ' + (Format-Value $Text)) }
}

# A refused call: status 1, the message, and no wsl.exe call at all.
function Assert-Refused($Result, [string]$Message, [int]$Calls = 0) {
    Assert-Equal 1 $Result.Code 'status'
    Assert-Text $Message $Result.Err 'message'
    Assert-Equal $Calls $Result.Calls.Count 'wsl.exe calls'
}

function Get-LaunchCall($Result) {
    Assert-Equal 2 $Result.Calls.Count 'wsl.exe calls (running list, launch)'
    Assert-Equal @('-l', '--running', '-q') $Result.Calls[0].Arguments.ToArray() 'list call'
    return $Result.Calls[1]
}

function Get-Argument($Result) {
    $call = Get-LaunchCall $Result
    if (-not $call.Env.ContainsKey('WRAPPER_WINDOWS_ARGS')) { return , @() }
    return , (ConvertFrom-Payload $call.Env['WRAPPER_WINDOWS_ARGS'])
}

function Clear-Setting([string]$Name) {
    if (Test-Path -LiteralPath ('Env:' + $Name)) { Remove-Item -LiteralPath ('Env:' + $Name) }
}

function Initialize-Case {
    foreach ($key in @([Environment]::GetEnvironmentVariables().Keys)) {
        if ([string]$key -cmatch '^(FAKE_WSL_|FIXTURE_|WRAPPER_WINDOWS_|WSL)|^(GH_TOKEN|USERPROFILE)$') {
            Clear-Setting ([string]$key)
        }
    }
    $env:FAKE_WSL_RECORD = $script:Record
    [IO.File]::WriteAllText((Join-Path $script:Checkout 'launcher/core.sh'), "#!/usr/bin/env bash`n:`n")
    Set-Location -LiteralPath $project
}

$script:Results = New-Object System.Collections.Generic.List[string]
$script:Failures = 0
function Test-Case([string]$Scenario, [scriptblock]$Body) {
    Initialize-Case
    try {
        & $Body
        $script:Results.Add('PASS ' + $Scenario)
    } catch {
        $script:Failures++
        $script:Results.Add('FAIL ' + $Scenario + ': ' + $_.Exception.Message)
    }
}

[void](New-Item -ItemType Directory -Force -Path $bin, $project)
$fakePath = Join-Path $bin 'wsl.exe'
[IO.File]::WriteAllText($fakePath, $fakeWsl)
& chmod 700 $fakePath
$env:PATH = $bin + [IO.Path]::PathSeparator + $env:PATH
$script:Checkout = Join-Path $work 'checkout'
$Entry = Build-Checkout $script:Checkout 'agent'
$Core = Join-Path $script:Checkout 'launcher/windows/core.ps1'
$shellCheckout = Join-Path $work 'shell-checkout'
$ShellEntry = Build-Checkout $shellCheckout 'shell-agent'
$e = [string][char]0x00E8
$emoji = [char]::ConvertFromUtf32(0x1F600)
$location = Get-Location

try {
    Test-Case 'Ordinary launches / Release bootstrap only; Default machine' {
        $r = Invoke-Entry { & $Entry -c true }
        Assert-Equal 0 $r.Code 'status'
        $call = Get-LaunchCall $r
        Assert-Equal '1' $r.Calls[0].Utf8 'WSL_UTF8 for the list'
        Assert-Equal $Launch $call.Arguments.ToArray() 'launch call'
        Assert-Equal 'unset' $call.Utf8 'WSL_UTF8 for the launch'
        Assert-Equal $project $call.Env['WRAPPER_WINDOWS_CWD'] 'working directory'
        Assert-Equal $script:Checkout $call.Env['WRAPPER_WINDOWS_ENTRY'] 'entry directory'
        Assert-Equal @('-c', 'true') (Get-Argument $r) 'arguments'
    }
    Test-Case 'Machine distribution and user selection / Default machine (older WSL writes UTF-16)' {
        $env:FAKE_WSL_UTF16 = '1'
        $r = Invoke-Entry { & $Entry }
        Assert-Equal 0 $r.Code 'status'
        Assert-Equal $Launch (Get-LaunchCall $r).Arguments.ToArray() 'launch call'
    }
    Test-Case 'Machine distribution and user selection / Other distribution and user' {
        $env:FIXTURE_AGENT_WSL_DISTRO = 'other-machine'
        $env:FIXTURE_AGENT_WSL_USER = 'dev'
        $env:FAKE_WSL_DISTROS = 'Ubuntu other-machine'
        $env:FAKE_WSL_USERS = 'dev'
        $r = Invoke-Entry { & $Entry }
        Assert-Equal 0 $r.Code 'status'
        Assert-Equal @('-d', 'other-machine', '-u', 'dev') (Get-LaunchCall $r).Arguments.GetRange(0, 4).ToArray() 'selection'
        Assert-True (-not ((Get-LaunchCall $r).WslEnv -match 'WSL_DISTRO')) '<P>_WSL_* is not forwarded'
    }
    Test-Case 'Machine distribution and user selection / Invalid name' {
        $env:FIXTURE_AGENT_WSL_DISTRO = 'bad name'
        Assert-Refused (Invoke-Entry { & $Entry }) 'FIXTURE_AGENT_WSL_DISTRO must contain only letters'
        $env:FIXTURE_AGENT_WSL_DISTRO = 'podman-machine-default'
        $env:FIXTURE_AGENT_WSL_USER = 'us"er'
        Assert-Refused (Invoke-Entry { & $Entry }) 'FIXTURE_AGENT_WSL_USER must contain only letters'
    }
    Test-Case 'Machine distribution and user selection / Missing distribution' {
        $env:FAKE_WSL_DISTROS = 'Ubuntu'
        $r = Invoke-Entry { & $Entry -c true }
        Assert-Refused $r 'the WSL distribution ''podman-machine-default'' is not registered' 2
        Assert-Text 'Podman Desktop' $r.Err 'guidance'
    }
    Test-Case 'Machine distribution and user selection / Missing user' {
        $env:FIXTURE_AGENT_WSL_USER = 'nobody'
        $r = Invoke-Entry { & $Entry -c true }
        Assert-Refused $r 'the user ''nobody'' does not exist in the WSL distribution ''podman-machine-default''' 3
        Assert-Equal @('-d', 'podman-machine-default', '-u', 'nobody', '--exec', '/bin/true') $r.Calls[2].Arguments.ToArray() 'user probe'
    }
    Test-Case 'Exit status, terminal and interruption / Exit status (255 from the session)' {
        $env:FAKE_WSL_EXIT = '255'
        $r = Invoke-Entry { & $Entry -c 'exit 255' }
        Assert-Equal 255 $r.Code 'status'
        Assert-Equal 3 $r.Calls.Count 'user probe after 255'
    }
    Test-Case 'Installation location and missing installation / Custom installation directory' {
        $env:FIXTURE_AGENT_WSL_INSTALLATION = '/home/user/sandbox'
        $r = Invoke-Entry { & $Entry }
        Assert-Equal 'cd && exec /bin/bash /home/user/sandbox/current/launcher/windows/bootstrap.sh' (Get-LaunchCall $r).Arguments[7] 'bootstrap'
        $env:FIXTURE_AGENT_WSL_INSTALLATION = 'home/user/sandbox'
        Assert-Refused (Invoke-Entry { & $Entry }) 'FIXTURE_AGENT_WSL_INSTALLATION must be an absolute distribution path'
    }
    Test-Case 'Installation location and missing installation / Machine reset' {
        $env:FAKE_WSL_EXIT = '127'
        $env:FAKE_WSL_INSTALLED = '1'
        $r = Invoke-Entry { & $Entry }
        Assert-Refused $r ('run .\' + $Name + '.ps1 --container-setup') 3
        Assert-Equal @('-d', 'podman-machine-default', '-u', 'user', '--exec', '/bin/sh', '-c', ('cd && test -f ' + $Bootstrap)) $r.Calls[2].Arguments.ToArray() 'installation probe'
        $env:FAKE_WSL_INSTALLED = '0'
        Assert-Equal 127 (Invoke-Entry { & $Entry }).Code '127 from the session'
    }
    Test-Case 'Arguments reach Bash unchanged / Quotes and empty values' {
        $r = Invoke-Entry { & $Entry -c 'printf "<%s>" "$@"' x '' 'a "b" c\' '\\server\x' ('tab' + "`t" + 'nl' + "`n" + 'end') }
        Assert-Equal @('-c', 'printf "<%s>" "$@"', 'x', '', 'a "b" c\', '\\server\x', ('tab' + "`t" + 'nl' + "`n" + 'end')) (Get-Argument $r) 'arguments'
        Assert-True (-not ($r.Calls[1].Arguments -contains 'x')) 'no argument value on the wsl.exe command line'
    }
    Test-Case 'Arguments reach Bash unchanged / Non-ASCII argument' {
        Assert-Equal @(($e + $emoji)) (Get-Argument (Invoke-Entry { & $Entry ($e + $emoji) })) 'arguments'
    }
    Test-Case 'Arguments reach Bash unchanged / No arguments and one empty argument differ' {
        $r = Invoke-Entry { & $Entry }
        Assert-True (-not ((Get-LaunchCall $r).WslEnv -match 'WRAPPER_WINDOWS_ARGS')) 'no transport variable without arguments'
        Assert-Equal @('') (Get-Argument (Invoke-Entry { & $Entry '' })) 'one empty argument'
    }
    Test-Case 'Arguments reach Bash unchanged / PowerShell binding of --, numbers and -x:y' {
        Assert-Equal @('x') (Get-Argument (Invoke-Entry { & $Entry -- x })) 'bare -- is consumed by PowerShell'
        Assert-Equal @('--', 'x', '5', '-x:', 'y') (Get-Argument (Invoke-Entry { & $Entry '--' x 5 -x:y })) 'quoted --, number, -x:y'
    }
    Test-Case 'Arguments reach Bash unchanged / Oversized arguments' {
        Assert-Equal 1 (Get-Argument (Invoke-Entry { & $Entry ('a' * 24572) })).Count 'largest accepted argument'
        Assert-Refused (Invoke-Entry { & $Entry ('a' * 24573) }) 'more than the 32766'
    }
    Test-Case 'Arguments reach Bash unchanged / Unquoted comma' {
        Assert-Refused (Invoke-Entry { & $Entry -c true a,b }) 'argument 3 is a list'
    }
    Test-Case 'Environment forwarded by name / Launch settings from PowerShell; Listed variable; Name reserved; Unrelated variable' {
        $env:FIXTURE_AGENT_MEMORY_LIMIT = '2g'
        $env:FIXTURE_AGENT_YOLO = '1'
        $env:FIXTURE_CONFIG_DIR = '/home/user/.fixture'
        $env:FIXTURE_AGENT_WSL_USER = 'user'
        $env:FIXTURE_AGENT_ENV_VARS = 'GH_TOKEN PATH  LD_PRELOAD PATH bad-name'
        $env:GH_TOKEN = 'secret'
        $env:USERPROFILE = 'C:\Users\me'
        $env:WSLENV = 'USERPROFILE/p'
        $r = Invoke-Entry { & $Entry }
        $call = Get-LaunchCall $r
        foreach ($pair in @(@('FIXTURE_AGENT_MEMORY_LIMIT', '2g'), @('FIXTURE_AGENT_YOLO', '1'),
                @('FIXTURE_CONFIG_DIR', '/home/user/.fixture'), @('GH_TOKEN', 'secret'),
                @('FIXTURE_AGENT_ENV_VARS', 'GH_TOKEN PATH  LD_PRELOAD PATH bad-name'))) {
            Assert-Equal $pair[1] $call.Env[$pair[0]] $pair[0]
        }
        foreach ($name in @('PATH', 'LD_PRELOAD', 'USERPROFILE', 'FIXTURE_AGENT_WSL_USER', 'bad-name')) {
            Assert-True (-not (($call.WslEnv -split ':') -contains ($name + '/u'))) ($name + ' is not forwarded')
        }
        Assert-True (-not $call.WslEnv.Contains('/p')) 'the user WSLENV is replaced'
        Assert-Equal 1 ([regex]::Matches($r.Err, 'PATH is not forwarded')).Count 'one notice for PATH'
        Assert-Text 'LD_PRELOAD is not forwarded' $r.Err 'notice for LD_PRELOAD'
    }
    Test-Case 'Environment forwarded by name / Name that would split WSLENV' {
        [Environment]::SetEnvironmentVariable('FIXTURE_AGENT_X:BASH_ENV/u', '/tmp/x')
        try {
            $r = Invoke-Entry { & $Entry }
            $call = Get-LaunchCall $r
            Assert-True (-not $call.WslEnv.Contains('BASH_ENV')) 'no BASH_ENV in WSLENV'
            Assert-Text 'FIXTURE_AGENT_X:BASH_ENV/u is not forwarded: not a valid variable name' $r.Err 'notice'
        } finally {
            [Environment]::SetEnvironmentVariable('FIXTURE_AGENT_X:BASH_ENV/u', $null)
        }
    }
    Test-Case 'Environment forwarded by name / Windows path in the configuration-directory variable' {
        $env:FIXTURE_CONFIG_DIR = 'C:\Users\me\.fixture'
        $r = Invoke-Entry { & $Entry }
        $call = Get-LaunchCall $r
        Assert-True (-not (($call.WslEnv -split ':') -contains 'FIXTURE_CONFIG_DIR/u')) 'Windows path not forwarded'
        Assert-Text 'FIXTURE_CONFIG_DIR is not forwarded: C:\Users\me\.fixture is not a path in the distribution' $r.Err 'notice'
    }
    Test-Case 'Empty Windows variables count as unset / Empty value in PowerShell 7' {
        [Environment]::SetEnvironmentVariable('FIXTURE_AGENT_MEMORY_LIMIT', '')
        $call = Get-LaunchCall (Invoke-Entry { & $Entry })
        Assert-True (-not $call.WslEnv.Contains('FIXTURE_AGENT_MEMORY_LIMIT')) 'empty value is not forwarded'
    }
    Test-Case 'Environment forwarded by name / Session environment restored' {
        $env:WSLENV = 'USERPROFILE/p'
        $env:WRAPPER_WINDOWS_CWD = 'previous'
        foreach ($status in @('0', '7')) {
            $env:FAKE_WSL_EXIT = $status
            $r = Invoke-Entry { & $Entry -c true }
            Assert-Equal ([int]$status) $r.Code 'status'
            Assert-Equal 'USERPROFILE/p' $env:WSLENV 'WSLENV'
            Assert-Equal 'previous' $env:WRAPPER_WINDOWS_CWD 'WRAPPER_WINDOWS_CWD'
            foreach ($name in @('WRAPPER_WINDOWS_ARGS', 'WRAPPER_WINDOWS_ENTRY', 'WSL_UTF8')) {
                Assert-True (-not (Test-Path -LiteralPath ('Env:' + $name))) ($name + ' stays absent')
            }
        }
    }
    Test-Case 'Windows working directory translation / Drive path with spaces (raw location passed on)' {
        Assert-Equal $project (Get-LaunchCall (Invoke-Entry { & $Entry })).Env['WRAPPER_WINDOWS_CWD'] 'raw location'
    }
    Test-Case 'Windows working directory translation / Registry location' {
        Set-Location -LiteralPath 'Env:'
        Assert-Refused (Invoke-Entry { & $Entry }) 'is not a file system path'
    }
    Test-Case 'Only unrestricted networking without delegation / Offline requested' {
        $env:FIXTURE_AGENT_NETWORK = 'offline'
        Assert-Refused (Invoke-Entry { & $Entry }) 'supports only unrestricted networking'
    }
    Test-Case 'Only unrestricted networking without delegation / Delegation requested' {
        $env:FIXTURE_AGENT_PODMAN = '1'
        Assert-Refused (Invoke-Entry { & $Entry }) 'delegation (FIXTURE_AGENT_PODMAN=1) is unsupported'
        Clear-Setting 'FIXTURE_AGENT_PODMAN'
        Assert-Refused (Invoke-Entry { & $Entry --container-qualify }) '--container-qualify verifies restricted modes'
    }
    Test-Case 'Only unrestricted networking without delegation / Mode from setup; explicit unrestricted' {
        $env:FIXTURE_AGENT_PODMAN = '0'
        Assert-Equal 0 (Invoke-Entry { & $Entry }).Code 'delegation disabled'
        $env:FIXTURE_AGENT_NETWORK = 'unrestricted'
        Assert-Equal 'unrestricted' (Get-LaunchCall (Invoke-Entry { & $Entry })).Env['FIXTURE_AGENT_NETWORK'] 'forwarded mode'
    }
    Test-Case 'Pipeline input refused, redirected input unchanged / Pipeline input' {
        Assert-Refused (Invoke-Entry { 'text' | & $Entry -c cat }) 'pipeline input is unsupported'
        $entryFile = Join-Path $script:Checkout ($Name + '.ps1')
        foreach ($line in @(@('pwsh', '-File', (Join-Path $work 'other.ps1')), @('powershell.exe', '-Command', '& x', '-File', $entryFile),
                @('powershell.exe', '-co', '& x', '-File', $entryFile), @('powershell.exe', '-E', 'eAA=', '-File', $entryFile))) {
            Assert-Refused (Invoke-Entry { & $Core -EntryDirectory $script:Checkout -Arguments @('-c', 'cat') -PipelineInput -CommandLine $line }) 'pipeline input is unsupported'
        }
    }
    Test-Case 'Pipeline input refused, redirected input unchanged / Redirected input (Windows PowerShell 5.1 -File)' {
        # 5.1 reports stdin redirected to powershell -File <entry> as pipeline input; no pipeline can feed that script.
        $line = @('powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-fil', (Join-Path $script:Checkout ($Name + '.ps1')).ToUpperInvariant(), '-c', 'cat')
        $r = Invoke-Entry { & $Core -EntryDirectory $script:Checkout -Arguments @('-c', 'cat') -PipelineInput -CommandLine $line }
        if ([Console]::IsInputRedirected) {
            Assert-Equal 0 $r.Code 'status'
            Assert-Equal @('-c', 'cat') (Get-Argument $r) 'arguments'
        } else {
            Assert-Refused $r 'pipeline input is unsupported'
        }
    }
    Test-Case 'Exit status, terminal and interruption / Exit status' {
        $env:FAKE_WSL_EXIT = '7'
        Assert-Equal 7 (Invoke-Entry { & $Entry -c 'exit 7' }).Code 'status'
    }
    Test-Case 'Windows entry help / Help with a machine (precedence over every other argument)' {
        $env:FIXTURE_AGENT_NETWORK = 'offline'
        $r = Invoke-Entry { & $Core -EntryDirectory $WinEntry -Arguments @('x', @('a', 'b'), '--container-help') -PipelineInput }
        Assert-Equal 0 $r.Code 'status'
        foreach ($text in @('FIXTURE_AGENT_WSL_DISTRO', 'FIXTURE_AGENT_WSL_USER', 'FIXTURE_AGENT_WSL_INSTALLATION', 'unrestricted', 'pipeline input')) {
            Assert-Text $text $r.Out 'Windows part'
        }
        Assert-Equal @('-d', 'podman-machine-default', '-u', 'user', '--cd', $WinEntry, '--exec', '/bin/bash', $agentProfile.wrapper, '--container-help') $r.Calls[1].Arguments.ToArray() 'wrapper help call'
        Assert-Equal '' $r.Calls[1].WslEnv 'no forwarded variables'
    }
    Test-Case 'Windows entry help / Help without a machine' {
        $env:FAKE_WSL_DISTROS = 'Ubuntu'
        $r = Invoke-Entry { & $Core -EntryDirectory $WinEntry -Arguments @('--container-help') }
        Assert-Equal 0 $r.Code 'status'
        Assert-Text 'FIXTURE_AGENT_WSL_DISTRO' $r.Out 'Windows part'
        Assert-Text 'Podman Desktop' $r.Out 'machine guidance'
        Assert-Equal 2 $r.Calls.Count 'only the two list calls'
    }
    Test-Case 'Machine started by Podman / Stopped machine' {
        $env:FAKE_WSL_RUNNING = 'none'
        $r = Invoke-Entry { & $Entry -c true }
        Assert-Refused $r 'the Podman machine is stopped: the WSL distribution ''podman-machine-default'' is not running' 2
        Assert-Text 'podman machine start' $r.Err 'start guidance'
        Assert-Equal @('-l', '-q') $r.Calls[1].Arguments.ToArray() 'second list call'
        $r = Invoke-Entry { & $Core -EntryDirectory $WinEntry -Arguments @('--container-setup') }
        Assert-Refused $r 'the Podman machine is stopped' 2
    }
    Test-Case 'Machine started by Podman / Distribution started by WSL alone (setup)' {
        $env:FAKE_WSL_RUNTIME = '1'
        $r = Invoke-Entry { & $Core -EntryDirectory $WinEntry -Arguments @('--container-setup') }
        Assert-Refused $r 'the WSL distribution ''podman-machine-default'' runs without the Podman machine' 2
        Assert-Text 'Run wsl --terminate podman-machine-default, then start the machine' $r.Err 'restart guidance'
        Assert-Equal @('-d', 'podman-machine-default', '-u', 'user', '--exec', '/bin/sh', '-c', 'test -d /run/user/$(id -u) -a -w /run/user/$(id -u)') $r.Calls[1].Arguments.ToArray() 'runtime probe'
        $env:FIXTURE_AGENT_WSL_USER = 'nobody'
        $r = Invoke-Entry { & $Core -EntryDirectory $WinEntry -Arguments @('--container-setup') }
        Assert-Refused $r 'the user ''nobody'' does not exist' 3
    }
    Test-Case 'Machine started by Podman / Help with a stopped machine' {
        $env:FAKE_WSL_RUNNING = 'none'
        $r = Invoke-Entry { & $Core -EntryDirectory $WinEntry -Arguments @('--container-help') }
        Assert-Equal 0 $r.Code 'status'
        Assert-Text 'FIXTURE_AGENT_WSL_DISTRO' $r.Out 'Windows part'
        Assert-Text 'The Podman machine is stopped' $r.Out 'machine guidance'
        Assert-Equal 2 $r.Calls.Count 'only the two list calls'
    }
    Test-Case 'Setup from the Windows checkout / First setup on Windows' {
        $env:WSLENV = 'USERPROFILE/p'
        $r = Invoke-Entry { & $Core -EntryDirectory $WinEntry -Arguments @('--container-setup') }
        Assert-Equal 0 $r.Code 'status'
        Assert-Equal 3 $r.Calls.Count 'running list, runtime probe, setup'
        Assert-Equal @('-d', 'podman-machine-default', '-u', 'user', '--cd', $WinEntry, '--exec', '/bin/bash', $agentProfile.wrapper, '--container-setup') $r.Calls[2].Arguments.ToArray() 'setup call'
        Assert-Equal '' $r.Calls[2].WslEnv 'no forwarded variables'
        Assert-Text ('start sessions with .\' + $Name + '.ps1 from a project directory') $r.Out 'next step'
        Assert-Equal 'USERPROFILE/p' $env:WSLENV 'WSLENV restored'
    }
    Test-Case 'Setup from the Windows checkout / Setup with other arguments' {
        Assert-Refused (Invoke-Entry { & $Core -EntryDirectory $WinEntry -Arguments @('--container-setup', '--container-shell') }) '--container-setup must be used alone'
        Assert-Refused (Invoke-Entry { & $Core -EntryDirectory '\\server\share\checkout' -Arguments @('--container-setup') }) 'is not a folder on a Windows drive'
    }
    Test-Case 'Checkout line endings checked before setup / Checkout converted to CRLF' {
        [IO.File]::WriteAllText((Join-Path $script:Checkout 'launcher/core.sh'), "#!/usr/bin/env bash`r`n:`r`n")
        $r = Invoke-Entry { & $Core -EntryDirectory $WinEntry -Arguments @('--container-setup') }
        Assert-Refused $r 'the checkout has CRLF line endings: launcher/core.sh'
        Assert-Text 'git rm -r -q --cached . and then git reset --hard' $r.Err 'renormalization step'
    }
    Test-Case 'Environment forwarded by name / Profile without an approval-bypass variable' {
        $env:FIXTURE_SHELL_CONFIG_DIR = '/home/user/.config/fixture-shell'
        $r = Invoke-Entry { & $ShellEntry -c true }
        Assert-Equal 0 $r.Code 'status'
        $call = Get-LaunchCall $r
        Assert-Equal '/home/user/.config/fixture-shell' $call.Env['FIXTURE_SHELL_CONFIG_DIR'] 'configuration directory'
        Assert-Equal ('cd && exec /bin/bash .local/lib/' + $shellProfile.name + '/current/launcher/windows/bootstrap.sh') $call.Arguments[7] 'bootstrap'
    }
} finally {
    Set-Location -LiteralPath $location
    Remove-Item -LiteralPath $work -Recurse -Force
}

foreach ($line in $script:Results) { [Console]::Out.WriteLine($line) }
[Console]::Out.WriteLine(('{0} cases, {1} failed' -f $script:Results.Count, $script:Failures))
if ($script:Failures -gt 0) { exit 1 }
