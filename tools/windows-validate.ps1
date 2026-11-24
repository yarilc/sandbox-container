# Operator validation of the Windows entry on a Windows host, with Windows
# PowerShell 5.1 or PowerShell 7. Reference-only: never copied.
#
# Run it after <name>.ps1 --container-setup, with the Podman machine set up and
# started by Podman, and another WSL distribution (for example Ubuntu) running.
# It stops at once when the machine is stopped, without starting it:
#
#   .\tools\windows-validate.ps1 [-Checkout <wrapper checkout>] [-StopMachine] [-Install] [-SavedDelegation]
#
# It runs the windows-launcher scenario matrix against the checkout's entry.
# Each case runs in a child process of the same PowerShell edition, so its
# arguments are parsed as in an interactive window and all of its output is
# captured. It prints one RESULT line per scenario and a summary for
# docs/validation.md, saved in the temporary directory, and removes the folders
# and drive letter it created. -StopMachine also checks the refusals of a
# stopped machine and of a distribution that wsl.exe alone started; it runs
# wsl.exe --terminate, which ends running sessions, and then restarts the
# machine with podman.exe when it is installed. -Install runs the installer
# from the checkout (answer its setup questions), launches the command through
# the new user PATH, and uninstalls; it refuses to start when an installation
# already exists, and changes the user PATH only for the time of the run.
# -SavedDelegation rewrites the installation's saved preferences as an earlier
# release with host Podman delegation saved them, checks that a launch stops,
# then reruns setup (answer its questions) and checks that the setting is gone;
# a cancelled or failed setup gets the preferences back.
# Ctrl+C, closing the window and the terminal size are checked by hand; the
# script prints how. The mode cases follow the network mode that setup saved:
# run the script after an offline setup for the restricted cases, and after an
# unrestricted one for the refusal of an unprepared restricted mode. The
# toolchain cases use a validation library of their own and need a release with
# the toolchain catalog: rerun setup after updating the checkout. The image
# toolchain case pulls a small pinned image into that library on the machine,
# and runs it from an offline session after an offline or provider setup.
# Bitdefender's Advanced Threat Control (Atc4.Detection) has blocked this
# script, which other antivirus products did not: run it with the checkout
# folder excluded, or with the protection paused for the run, as the
# administrator allows (README, Limits on Windows).
param(
    [string]$Checkout = (Split-Path -Parent $PSScriptRoot),
    [switch]$StopMachine,
    [switch]$Install,
    [switch]$SavedDelegation
)
Set-StrictMode -Version 3
$ErrorActionPreference = 'Stop'

$Checkout = (Resolve-Path -LiteralPath $Checkout).ProviderPath
$wrapperProfile = [IO.File]::ReadAllText([IO.Path]::Combine($Checkout, 'agent', 'profile.json')) | ConvertFrom-Json
$name = $wrapperProfile.name
$P = $wrapperProfile.env_prefix
# An agent wrapper passes every other argument to its agent, so -c reaches Bash
# only after --container-shell. The cases splat $C before -c.
$shellOption = ''
if ($wrapperProfile.native.command -cne 'bash') { $shellOption = '--container-shell' }
$entry = [IO.Path]::Combine($Checkout, $name + '.ps1')
$exe = (Get-Process -Id $PID).Path
$distro = [Environment]::GetEnvironmentVariable($P + '_WSL_DISTRO')
if ([string]::IsNullOrEmpty($distro)) { $distro = 'podman-machine-default' }
$user = [Environment]::GetEnvironmentVariable($P + '_WSL_USER')
if ([string]::IsNullOrEmpty($user)) { $user = 'user' }
$sessionLabel = $wrapperProfile.label_namespace + '.session'
$installation = [Environment]::GetEnvironmentVariable($P + '_WSL_INSTALLATION')
if ([string]::IsNullOrEmpty($installation)) {
    $bootstrap = '.local/lib/' + $name + '/current/launcher/windows/bootstrap.sh'
} else {
    $bootstrap = $installation + '/current/launcher/windows/bootstrap.sh'
}
# Next to the checkout: AppData (and TEMP inside it) is a refused workspace, and
# TEMP can also be an 8.3 short path, which the distribution cannot resolve.
$work = Join-Path (Split-Path -Parent $Checkout) ($name + '-windows-validate')
$project = Join-Path $work 'project with spaces'
$sibling = Join-Path (Split-Path -Parent $Checkout) ($name + '-validate-sibling')
$summaryFile = Join-Path ([IO.Path]::GetTempPath()) ($name + '-windows-validate-' + $PSVersionTable.PSEdition + '.txt')
$results = New-Object System.Collections.Generic.List[string]
$substDrive = $null
$localData = [Environment]::GetEnvironmentVariable('LOCALAPPDATA')
if ([string]::IsNullOrEmpty($localData)) { $localData = [Environment]::GetFolderPath('LocalApplicationData') }
$installFolder = [IO.Path]::GetFullPath([IO.Path]::Combine($localData, 'Programs', $name))
if ($Install) {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        [Console]::Error.WriteLine('-Install needs Windows: it changes the user PATH in the registry')
        exit 2
    }
    if (Test-Path -LiteralPath $installFolder) {
        [Console]::Error.WriteLine('-Install refuses to start: ' + $installFolder + ' exists; run ' + $name +
            ' --container-uninstall first')
        exit 2
    }
}

function ConvertTo-Literal([string]$Text) { return "'" + $Text.Replace("'", "''") + "'" }

function Add-Result([string]$Outcome, [string]$Scenario, [string]$Detail) {
    $line = 'RESULT ' + $Outcome + ' ' + $Scenario + ': ' + $Detail
    $results.Add($line)
    [Console]::Out.WriteLine($line)
}

# Starts a process with all streams redirected; stdin is closed at once.
function Invoke-Process([string]$FileName, [string]$ArgumentLine, [string]$Directory) {
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $FileName
    $info.Arguments = $ArgumentLine
    $info.WorkingDirectory = $Directory
    $info.UseShellExecute = $false
    $info.RedirectStandardInput = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $process = [System.Diagnostics.Process]::Start($info)
    $process.StandardInput.Close()
    $out = $process.StandardOutput.ReadToEndAsync()
    $err = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit(600000)) {
        $process.Kill()
        return [pscustomobject]@{ Code = 'timeout'; Out = ''; Err = 'timed out after 600 s' }
    }
    $process.WaitForExit()
    return [pscustomobject]@{ Code = $process.ExitCode; Out = $out.Result; Err = $err.Result }
}

# The command line of a child of this edition that runs PowerShell code. $E is
# the entry. The child starts without the operator's <P>_* settings (except
# <P>_WSL_*) and WSLENV.
function Get-CaseArgument([string]$Body, [string]$Location) {
    $lines = @(
        '$ErrorActionPreference = ''Continue''',
        ('$E = ' + (ConvertTo-Literal $entry)),
        ('$C = @(' + $(if ($shellOption) { ConvertTo-Literal $shellOption } else { '' }) + ')'),
        ('foreach ($k in @([Environment]::GetEnvironmentVariables().Keys)) { if (([string]$k).StartsWith(' +
            (ConvertTo-Literal ($P + '_')) + ') -and -not ([string]$k).StartsWith(' + (ConvertTo-Literal ($P + '_WSL_')) +
            ')) { Remove-Item -LiteralPath (''Env:'' + $k) } }'),
        'if (Test-Path Env:WSLENV) { Remove-Item Env:WSLENV }',
        ('Set-Location -LiteralPath ' + (ConvertTo-Literal $Location)),
        $Body,
        'exit $LASTEXITCODE'
    )
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes(($lines -join "`n")))
    return ('-NoProfile -NonInteractive -OutputFormat Text -EncodedCommand ' + $encoded)
}

function Invoke-Case([string]$Body, [string]$Location = $project) {
    return (Invoke-Process $exe (Get-CaseArgument $Body $Location) $work)
}

# The same without waiting: the process, and its output when it ends.
function Invoke-BackgroundCase([string]$Body) {
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $exe
    $info.Arguments = Get-CaseArgument $Body $project
    $info.WorkingDirectory = $work
    $info.UseShellExecute = $false
    $info.RedirectStandardInput = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $process = [System.Diagnostics.Process]::Start($info)
    $process.StandardInput.Close()
    return [pscustomobject]@{ Process = $process; Out = $process.StandardOutput.ReadToEndAsync();
        Err = $process.StandardError.ReadToEndAsync() }
}

# The first line of text. A Windows PowerShell 5.1 child started with
# -EncodedCommand also writes CLIXML (progress records) to stderr; it is dropped.
function Get-FirstLine([string]$Text) {
    $plain = $Text -replace '#< CLIXML', '' -replace '(?s)<Obj S="progress".*?</Obj>', '' -replace '</?Objs[^>]*>', ''
    foreach ($line in ($plain -split "`r?`n")) { if ($line.Trim()) { return $line.Trim() } }
    return '(no output)'
}

# The last line of a failed case's error output: launch notices come first, the
# error that ended the launch comes last.
function Get-LastLine([string]$Text) {
    $plain = $Text -replace '#< CLIXML', '' -replace '(?s)<Obj S="progress".*?</Obj>', '' -replace '</?Objs[^>]*>', ''
    $lines = @($plain -split "`r?`n" | Where-Object { $_.Trim() })
    if ($lines.Count -gt 1) { return ' | last: ' + $lines[-1].Trim() }
    return ''
}

# Records a case: the expected status and a text expected in the output.
function Test-Outcome([string]$Scenario, $Result, [int]$Code, [string]$Text) {
    $all = $Result.Out + "`n" + $Result.Err
    if ($Result.Code -eq $Code -and $all.Contains($Text)) {
        Add-Result 'PASS' $Scenario ('status ' + $Result.Code + '; ' + (Get-FirstLine $(if ($Code -eq 0) { $Result.Out } else { $Result.Err })))
    } else {
        Add-Result 'FAIL' $Scenario ('status ' + $Result.Code + ' (expected ' + $Code + ', text ''' + $Text + '''); out: ' +
            (Get-FirstLine $Result.Out) + '; err: ' + (Get-FirstLine $Result.Err) + (Get-LastLine $Result.Err))
    }
}

# wsl.exe --terminate, then wait until WSL no longer lists the distribution as
# running, and a little longer: in round 5, podman machine start right after a
# terminate failed in the machine's bootstrap and left WSL unresponsive.
function Invoke-DistributionStop {
    $null = Invoke-Probe @('--terminate', $distro)
    for ($i = 0; $i -lt 30; $i++) {
        $running = Invoke-Probe @('-l', '--running', '-q')
        if (-not (@($running.Output | ForEach-Object { $_.Trim() }) -contains $distro)) { break }
        Start-Sleep -Seconds 1
    }
    Start-Sleep -Seconds 5
}

function ConvertTo-Hex([string]$Text) {
    return ((@([Text.Encoding]::UTF8.GetBytes($Text)) | ForEach-Object { $_.ToString('x2') }) -join '')
}

# Runs a sh script through the machine's launch service, in the machine's
# systemd namespaces (the checkout's helper). The script holds no double quote,
# which Windows PowerShell 5.1 would break on the wsl.exe command line.
function Invoke-ServicePodman([string]$Script) {
    return Invoke-Probe @('-d', $distro, '-u', $user, '--cd', $Checkout, '--exec', '/bin/bash',
        'launcher/windows/enter.sh', $name, '/bin/sh', '-c',
        ('service=unix://$XDG_RUNTIME_DIR/podman/podman.sock; ' + $Script))
}

function Invoke-Probe([string[]]$WslArguments) {
    $ErrorActionPreference = 'Continue'
    $saved = [Environment]::GetEnvironmentVariable('WSL_UTF8')
    $env:WSL_UTF8 = '1'
    try {
        $output = @(& wsl.exe @WslArguments 2>&1 | ForEach-Object { ([string]$_) -replace "`0", '' })
        return [pscustomobject]@{ Code = $LASTEXITCODE; Output = $output }
    } finally {
        if ($null -eq $saved) { Remove-Item Env:WSL_UTF8 } else { $env:WSL_UTF8 = $saved }
    }
}

[void](New-Item -ItemType Directory -Force -Path $project)
try {
    $wslVersion = Invoke-Probe @('--version')
    $results.Add('Checkout: ' + $Checkout + '; entry: ' + $name + '.ps1')
    $results.Add('PowerShell ' + $PSVersionTable.PSVersion + ' ' + $PSVersionTable.PSEdition + '; ' +
        (($wslVersion.Output | Where-Object { $_.Trim() } | Select-Object -First 2) -join '; '))
    $running = Invoke-Probe @('-l', '--running', '-q')
    $others = @($running.Output | ForEach-Object { $_.Trim() } | Where-Object { $_ -and $_ -ne $distro })
    $results.Add('Distribution: ' + $distro + ', user ' + $user + '; other running distributions: ' + ($others -join ', '))
    foreach ($line in $results) { [Console]::Out.WriteLine($line) }

    # The machine must run, started by Podman, before any wsl.exe -d call: such a
    # call would start a stopped distribution without Podman, and every case
    # would then fail.
    if (-not (@($running.Output | ForEach-Object { $_.Trim() }) -contains $distro)) {
        Add-Result 'FAIL' 'Machine running' ('the Podman machine is stopped: the WSL distribution ''' + $distro +
            ''' is not running. Start it with Podman Desktop or podman machine start, then run this script again')
        exit 2
    }
    $runtimeProbe = Invoke-Probe @('-d', $distro, '-u', $user, '--exec', '/bin/sh', '-c',
        'test -d /run/user/$(id -u) -a -w /run/user/$(id -u)')
    if ($runtimeProbe.Code -ne 0) {
        Add-Result 'FAIL' 'Machine running' ('the WSL distribution ''' + $distro + ''' runs without the Podman ' +
            'machine (no /run/user/<uid>). Run wsl --terminate ' + $distro + ', then start the machine with Podman ' +
            'Desktop or podman machine start, and run this script again')
        exit 2
    }
    Add-Result 'PASS' 'Machine running' ('started by Podman; /run/user/<uid> present')

    # Setup state: the release bootstrap must exist.
    $state = Invoke-Probe @('-d', $distro, '-u', $user, '--exec', '/bin/sh', '-c', ('cd && test -f ' + $bootstrap))
    if ($state.Code -ne 0) {
        Add-Result 'FAIL' 'Setup state' ('no installation (' + $bootstrap + '); run .\' + $name + '.ps1 --container-setup first')
        return
    }
    Add-Result 'PASS' 'Setup state' ('release bootstrap present: ' + $bootstrap)
    # The worktree scope that setup saved. With it, every launch mounts the parent
    # of its folder, so the cases that assume no scope are skipped, and the
    # toolchain case that needs it runs.
    $setupFile = $bootstrap.Replace('launcher/windows/bootstrap.sh', 'setup.json')
    $scopeProbe = Invoke-Probe @('-d', $distro, '-u', $user, '--exec', '/bin/sh', '-c',
        ('cd && grep -Eq ''worktree.: *true'' ' + $setupFile))
    $scopeSaved = ($scopeProbe.Code -eq 0)
    $scopeSkip = 'setup saved the worktree scope, so this launch mounts the parent folder; run the script again ' +
        'after a setup without it'
    if ($others.Count -eq 0) { Add-Result 'SKIP' 'Another distribution is active' 'start another WSL distribution and rerun' }

    $r = Invoke-Case '& $E @C -c ''printf ok'''
    Test-Outcome 'Ordinary launch; Mode from setup' $r 0 'network mode='
    $savedMode = ''
    if (($r.Out + "`n" + $r.Err) -match 'network mode=([a-z]+)') { $savedMode = $Matches[1] }
    if ($others.Count -gt 0) { Test-Outcome ('Another distribution is active (' + ($others -join ', ') + ')') $r 0 'ok' }

    Test-Outcome 'Exit status' (Invoke-Case '& $E @C -c ''exit 7''') 7 ''

    # Arguments, compared as hex so that console code pages do not matter.
    $nonAscii = [string][char]0x00E8 + [char]::ConvertFromUtf32(0x1F600)
    $r = Invoke-Case ('& $E @C -c ''for a; do printf "[%s]\n" "$(printf %s "$a" | od -An -tx1 | tr -d " \n")"; done'' _ x '''' ''a "b" c\'' ''--'' ' +
        '([string][char]0x00E8 + [char]::ConvertFromUtf32(0x1F600))')
    $expected = (@('x', '', 'a "b" c\', '--', $nonAscii) | ForEach-Object { '[' + (ConvertTo-Hex $_) + ']' }) -join ','
    $got = (@($r.Out -split "`r?`n" | Where-Object { $_ -match '^\[' }) -join ',')
    if ($r.Code -eq 0 -and $got -eq $expected) { Add-Result 'PASS' 'Quotes and empty values; Non-ASCII argument' $got }
    else { Add-Result 'FAIL' 'Quotes and empty values; Non-ASCII argument' ('status ' + $r.Code + ' got ' + $got + ' expected ' + $expected + '; err: ' + (Get-FirstLine $r.Err)) }
    Test-Outcome 'Unquoted comma' (Invoke-Case '& $E @C -c true a,b') 1 'is a list'
    Test-Outcome 'Oversized arguments' (Invoke-Case '& $E (''a'' * 24573)') 1 '32766'
    Test-Outcome 'Pipeline input' (Invoke-Case '''x'' | & $E @C -c cat') 1 'pipeline input is unsupported'

    # Environment: forwarded by name, reserved, unrelated and empty variables, restoration.
    $r = Invoke-Case (('$env:{0}_ENV_VARS = ''VALIDATE_LISTED VALIDATE_EMPTY PATH''; $env:VALIDATE_LISTED = ''listed value''; ' +
        '$env:VALIDATE_UNLISTED = ''x''; [Environment]::SetEnvironmentVariable(''VALIDATE_EMPTY'', ''''); ' +
        '$env:WSLENV = ''USERPROFILE/p''; & $E @C -c ''printf "%s|%s|%s\n" "${{VALIDATE_LISTED-unset}}" "${{VALIDATE_UNLISTED-unset}}" "${{VALIDATE_EMPTY-unset}}"''; ' +
        '$c = $LASTEXITCODE; ''WSLENV='' + $env:WSLENV; ''ABSENT='' + (Test-Path Env:WRAPPER_WINDOWS_ARGS) + (Test-Path Env:WRAPPER_WINDOWS_ENTRY); exit $c') -f $P)
    Test-Outcome 'Listed variable; Unrelated Windows variable; Empty value' $r 0 'listed value|unset|unset'
    Test-Outcome 'Name reserved by the distribution' $r 0 'PATH is not forwarded'
    Test-Outcome 'Session environment restored (WSLENV)' $r 0 'WSLENV=USERPROFILE/p'
    Test-Outcome 'Session environment restored (absent variables stay absent)' $r 0 'ABSENT=FalseFalse'

    # Working directory.
    $drive = $project.Substring(0, 1).ToLowerInvariant()
    $mount = '/mnt/' + $drive + $project.Substring(2).Replace('\', '/')
    Test-Outcome 'Drive path with spaces' (Invoke-Case '& $E @C -c pwd') 0 $mount
    $inside = '\\wsl.localhost\' + $distro + '\tmp'
    if (Test-Path -LiteralPath $inside) {
        Test-Outcome 'Path inside a WSL distribution' (Invoke-Case '& $E' $inside) 1 'inside a WSL distribution'
    } else { Add-Result 'SKIP' 'Path inside a WSL distribution' ($inside + ' is not reachable') }
    $share = '\\localhost\' + $project.Substring(0, 1) + '$' + $project.Substring(2)
    if (Test-Path -LiteralPath $share) {
        Test-Outcome 'Network share' (Invoke-Case '& $E' $share) 1 'network or device path'
    } else { Add-Result 'SKIP' 'Network share' ($share + ' is not reachable (administrative share)') }
    if (Get-Command -Name 'subst.exe' -CommandType Application -ErrorAction SilentlyContinue) {
        $used = @([IO.DriveInfo]::GetDrives() | ForEach-Object { $_.Name.Substring(0, 1).ToUpperInvariant() })
        foreach ($letter in @('Y', 'X', 'W', 'V', 'U', 'T')) { if ($used -notcontains $letter) { $substDrive = $letter + ':'; break } }
    }
    if ($null -ne $substDrive) {
        & subst.exe $substDrive $work
        Test-Outcome ('Drive not mounted (' + $substDrive + ' from subst)') (Invoke-Case '& $E' ($substDrive + '\project with spaces')) 1 'which this distribution does not mount'
    } else { Add-Result 'SKIP' 'Drive not mounted' 'subst.exe or a free drive letter is unavailable' }
    if (Test-Path -LiteralPath 'HKCU:\Software') {
        Test-Outcome 'Registry location' (Invoke-Case '& $E' 'HKCU:\Software') 1 'not a file system path'
    } else { Add-Result 'SKIP' 'Registry location' 'no HKCU: drive' }

    # Windows folders refused by the core.
    $profileDirectory = [Environment]::GetFolderPath('UserProfile')
    $windowsDirectory = [Environment]::GetFolderPath('Windows')
    if ($profileDirectory -and $windowsDirectory) {
        Test-Outcome 'Windows folders: profile' (Invoke-Case '& $E' $profileDirectory) 1 'refusing sensitive workspace'
        Test-Outcome 'Windows folders: profile in lower case' (Invoke-Case '& $E' $profileDirectory.ToLowerInvariant()) 1 'refusing sensitive workspace'
        if ($scopeSaved) {
            # The parent of these folders is the drive root, which contains the
            # checkout: the entry-directory refusal comes first.
            Add-Result 'SKIP' 'Windows folders: Users' $scopeSkip
            Add-Result 'SKIP' 'Windows folders: Windows' $scopeSkip
        } else {
            Test-Outcome 'Windows folders: Users' (Invoke-Case '& $E' (Split-Path -Parent $profileDirectory)) 1 'refusing sensitive workspace'
            Test-Outcome 'Windows folders: Windows' (Invoke-Case '& $E' $windowsDirectory) 1 'refusing sensitive workspace'
        }
        $documents = [Environment]::GetFolderPath('MyDocuments')
        if ($documents) {
            Test-Outcome 'Windows folders: Documents' (Invoke-Case '& $E' $documents) 1 'refusing sensitive workspace'
        }
        $localData = [Environment]::GetFolderPath('LocalApplicationData')
        if ($localData) {
            Test-Outcome 'Windows folders: inside AppData' (Invoke-Case '& $E' $localData) 1 'refusing sensitive workspace'
        }
    } else { Add-Result 'SKIP' 'Windows folders' 'no Windows profile or system folder' }

    # Modes: as setup prepared them; delegation stays refused.
    Test-Outcome 'Delegation requested' (Invoke-Case ('$env:' + $P + '_PODMAN = ''1''; & $E')) 1 ($P + '_PODMAN=1: host Podman delegation was removed')
    Test-Outcome 'Explicit unrestricted networking' (Invoke-Case ('$env:' + $P + '_NETWORK = ''unrestricted''; & $E @C -c ''printf ok''')) 0 'ok'
    if ($savedMode -eq 'offline' -or $savedMode -eq 'provider') {
        $connect = 'if (exec 3<>/dev/tcp/1.1.1.1/443) 2>/dev/null; then echo reached; else echo blocked; fi'
        if ($savedMode -eq 'provider') {
            # Qualification reports are per network mode, and setup qualified
            # provider only: an offline session needs its own qualification.
            Test-Outcome 'Offline qualification' (Invoke-Case ('$env:' + $P + '_NETWORK = ''offline''; & $E --container-qualify')) 0 'status='
        }
        Test-Outcome 'Offline session (no network access)' (Invoke-Case ('$env:' + $P + '_NETWORK = ''offline''; & $E @C -c ' +
            (ConvertTo-Literal $connect))) 0 'blocked'
        Test-Outcome 'Qualification' (Invoke-Case '& $E --container-qualify') 0 'status='
        Add-Result 'SKIP' 'Restricted mode without a prepared installation' ('setup saved ' + $savedMode +
            ' networking; run the script again after an unrestricted setup')
    } else {
        # The launcher's guidance names the Windows step, not the wrapper path in the machine.
        Test-Outcome 'Restricted mode without a prepared installation' (Invoke-Case ('$env:' + $P + '_NETWORK = ''offline''; & $E @C -c true')) 1 ('setup required: offline sessions need a protected installation; run ' + $name + '.ps1 --container-setup from Windows')
        Add-Result 'SKIP' 'Offline session; Qualification' ('setup saved ' + $savedMode + ' networking; run .\' + $name +
            '.ps1 --container-setup with offline networking, then the script again')
    }

    # One engine: the machine's launch service runs a command in, and removes, a
    # running session's container. Other running sessions of this wrapper would
    # also match the label. A session's container engine carries the same label,
    # and the session depends on it, so engines are left out of the listing.
    $background = Invoke-BackgroundCase '& $E @C -c ''sleep 60'''
    $container = ''
    for ($i = 0; $i -lt 45 -and -not $container; $i++) {
        Start-Sleep -Seconds 2
        $listed = Invoke-ServicePodman ('engines=$XDG_RUNTIME_DIR/validate-engines.$$; ' +
            'podman --remote --url $service ps --filter label=' + $sessionLabel +
            ' --filter label=sandbox-engine.owner --format {{.ID}} > $engines; ' +
            'podman --remote --url $service ps --filter label=' + $sessionLabel +
            ' --format {{.ID}} | grep -vxF -f $engines; rm -f $engines')
        $container = @($listed.Output | ForEach-Object { $_.Trim() } | Where-Object { $_ -cmatch '^[0-9a-f]{12,64}$' } |
            Select-Object -First 1) -join ''
    }
    if (-not $container) {
        Add-Result 'FAIL' 'One engine for sessions and the machine' 'the service listed no session container within 90 s'
    } else {
        $exec = Invoke-ServicePodman ('podman --remote --url $service exec ' + $container + ' /bin/true')
        $removed = Invoke-ServicePodman ('podman --remote --url $service rm -f -t 0 ' + $container)
        $ended = $background.Process.WaitForExit(60000)
        $left = Invoke-ServicePodman ('podman --remote --url $service ps -a --filter id=' + $container + ' --format {{.ID}}')
        $remaining = @($left.Output | Where-Object { $_.Trim() }).Count
        if ($exec.Code -eq 0 -and $removed.Code -eq 0 -and $ended -and $remaining -eq 0) {
            Add-Result 'PASS' 'One engine for sessions and the machine' ('the service ran a command in ' + $container +
                ' and removed it; the session ended with status ' + $background.Process.ExitCode)
        } else {
            Add-Result 'FAIL' 'One engine for sessions and the machine' ('exec status ' + $exec.Code + ' (' +
                (($exec.Output | Select-Object -First 2) -join ' ') + '); rm status ' + $removed.Code + ' (' +
                (($removed.Output | Select-Object -Last 1) -join ' ') + '); session ended: ' + $ended + '; containers left: ' + $remaining)
        }
    }
    if (-not $background.Process.HasExited) { $background.Process.Kill() }

    # Entry directory outside writable mounts.
    Test-Outcome 'Launch from the checkout' (Invoke-Case '& $E @C -c true' $Checkout) 1 'overlaps the writable mount'
    Test-Outcome 'Different letter case' (Invoke-Case '& $E @C -c true' $Checkout.ToUpperInvariant()) 1 'overlaps the writable mount'
    if (Test-Path -LiteralPath $sibling) {
        Add-Result 'SKIP' 'Sibling checks' ($sibling + ' already exists')
    } else {
        [void](New-Item -ItemType Directory -Path $sibling)
        Test-Outcome 'Worktree scope with a sibling checkout' (Invoke-Case '& $E @C --container-git-worktree -c true' $sibling) 1 'overlaps the writable mount'
        if ($scopeSaved) {
            Add-Result 'SKIP' 'Sibling without worktree scope' $scopeSkip
        } else {
            Test-Outcome 'Sibling without worktree scope' (Invoke-Case '& $E @C -c ''printf ok''' $sibling) 0 'ok'
        }
        Remove-Item -LiteralPath $sibling -Recurse -Force
    }

    # Redirected input through cmd.exe reaches the session unchanged.
    if (Get-Command -Name 'cmd.exe' -CommandType Application -ErrorAction SilentlyContinue) {
        $inputFile = Join-Path $work 'input.bin'
        [IO.File]::WriteAllBytes($inputFile, [byte[]](0x61, 0x0a, 0xc3, 0xa8, 0x0d, 0x0a, 0x00, 0x7a))
        # An agent wrapper needs --container-shell for -c to reach Bash, as $C does above.
        $shellArgument = ''
        if ($shellOption) { $shellArgument = $shellOption + ' ' }
        $r = Invoke-Process 'cmd.exe' ('/d /s /c ""' + $exe + '" -NoProfile -NonInteractive -File "' + $entry +
            '" ' + $shellArgument + '-c "od -An -tx1" < "' + $inputFile + '""') $project
        $hex = ($r.Out -replace '\s', '')
        if ($r.Code -eq 0 -and $hex.EndsWith('610ac3a80d0a007a')) { Add-Result 'PASS' 'Redirected input' $hex }
        else { Add-Result 'FAIL' 'Redirected input' ('status ' + $r.Code + ' got ' + $hex + '; err: ' + (Get-FirstLine $r.Err) + (Get-LastLine $r.Err)) }
    } else { Add-Result 'SKIP' 'Redirected input' 'no cmd.exe' }

    # Distribution, user and installation diagnosis.
    Test-Outcome 'Missing installation' (Invoke-Case ('$env:' + $P + '_WSL_INSTALLATION = ''/nonexistent/validate''; & $E')) 1 ('.\' + $name + '.ps1 --container-setup')
    Test-Outcome 'Missing distribution' (Invoke-Case ('$env:' + $P + '_WSL_DISTRO = ''validate-missing''; & $E')) 1 'is not registered'
    Test-Outcome 'Missing user' (Invoke-Case ('$env:' + $P + '_WSL_USER = ''validate-missing''; & $E')) 1 'does not exist'
    Test-Outcome 'Invalid name' (Invoke-Case ('$env:' + $P + '_WSL_DISTRO = ''bad name''; & $E')) 1 'must contain only letters'

    # Help and setup routing.
    $r = Invoke-Case '& $E --container-help'
    Test-Outcome 'Help with a machine (Windows part)' $r 0 ($P + '_WSL_DISTRO')
    Test-Outcome 'Help with a machine (wrapper help)' $r 0 'Usage:'
    Test-Outcome 'Help without a machine' (Invoke-Case ('$env:' + $P + '_WSL_DISTRO = ''validate-missing''; & $E --container-help')) 0 'Podman Desktop'
    Test-Outcome 'Setup with other arguments' (Invoke-Case '& $E --container-setup --container-shell') 1 'must be used alone'

    # Toolchain library, in a validation library of its own: a catalog name, a
    # Windows recipe path, a network path and, when setup saved it, the worktree
    # scope. The recipe folder is outside $work, which that scope mounts.
    $homeProbe = Invoke-Probe @('-d', $distro, '-u', $user, '--exec', '/bin/sh', '-c', 'printf %s $HOME')
    $machineHome = (@($homeProbe.Output) -join '').Trim()
    $recipeFolder = Join-Path (Split-Path -Parent $Checkout) ($name + '-validate-recipes')
    if ($homeProbe.Code -ne 0 -or -not $machineHome.StartsWith('/')) {
        Add-Result 'SKIP' 'Toolchain library' 'the home directory of the machine user is unknown'
    } elseif (Test-Path -LiteralPath $recipeFolder) {
        Add-Result 'SKIP' 'Toolchain library' ($recipeFolder + ' already exists')
    } else {
        $library = $machineHome + '/' + $name + '-validate-toolchains'
        $useLibrary = '$env:' + $P + '_TOOLCHAINS_DIR = ' + (ConvertTo-Literal $library) + '; '
        try {
            Test-Outcome 'Toolchain by name' (Invoke-Case ($useLibrary + '& $E --container-toolchain add node24')) 0 'Added toolchain node24'
            [void](New-Item -ItemType Directory -Path $recipeFolder)
            $recipeFile = Join-Path $recipeFolder 'node24.json'
            Copy-Item -LiteralPath ([IO.Path]::Combine($Checkout, 'setup', 'toolchain-catalog', 'node24.json')) -Destination $recipeFile
            Test-Outcome 'Recipe path from PowerShell' (Invoke-Case ($useLibrary + '& $E --container-toolchain add ' +
                (ConvertTo-Literal $recipeFile))) 0 'Added toolchain node24'
            Test-Outcome 'Toolchain recipe on a network share' (Invoke-Case ($useLibrary +
                '& $E --container-toolchain add ''\\server\share\node24.json''')) 1 'network or device path'
            $listing = Invoke-Case ($useLibrary + '& $E --container-toolchain list')
            if ($scopeSaved) {
                Test-Outcome 'Toolchain command with the saved worktree scope' $listing 0 'node24'
            } else {
                Test-Outcome 'Toolchain list' $listing 0 'node24'
                Add-Result 'SKIP' 'Toolchain command with the saved worktree scope' ('setup saved no worktree ' +
                    'scope; run the script again after a setup that saves it')
            }
            # Image toolchain: the image enters the library's store, and an offline
            # session runs it through its private engine, without a pull and with
            # no network path in the nested container.
            $image = 'docker.io/library/alpine@sha256:c64c687cbea9300178b30c95835354e34c4e4febc4badfe27102879de0483b5e'
            $imageRecipe = Join-Path $recipeFolder 'validate-image.json'
            [IO.File]::WriteAllText($imageRecipe, ('{"schema": 2, "name": "validate-image", "version": "1", ' +
                '"default": false, "images": ["' + $image + '"], ' +
                '"check": ["podman", "run", "--rm", "--network=none", "' + $image + '", "true"]}'))
            Test-Outcome 'Image toolchain' (Invoke-Case ($useLibrary + '& $E --container-toolchain add ' +
                (ConvertTo-Literal $imageRecipe))) 0 'Added toolchain validate-image'
            if ($savedMode -eq 'offline' -or $savedMode -eq 'provider') {
                $nested = 'printf "engine=%s\n" "$CONTAINER_HOST"; podman run --rm --pull=never ' + $image +
                    ' sh -c ''if wget -q -T 3 -O /dev/null http://1.1.1.1/ 2>/dev/null; then echo reached; ' +
                    'else echo nested-blocked; fi'''
                $r = Invoke-Case ($useLibrary + '$env:' + $P + '_NETWORK = ''offline''; & $E @C -c ' +
                    (ConvertTo-Literal $nested))
                Test-Outcome 'Session with library images (engine)' $r 0 'engine=tcp://127.0.0.1:2375'
                Test-Outcome 'Session with library images (offline)' $r 0 'nested-blocked'
            } else {
                Add-Result 'SKIP' 'Session with library images' ('setup saved ' + $savedMode +
                    ' networking; run .\' + $name + '.ps1 --container-setup with offline networking, then the script again')
            }
            Test-Outcome 'Image toolchain removed' (Invoke-Case ($useLibrary +
                '& $E --container-toolchain remove validate-image')) 0 'Removed toolchain validate-image'
        } finally {
            # Image layers in the store can belong to subordinate IDs.
            $null = Invoke-Probe @('-d', $distro, '-u', $user, '--exec', 'podman', 'unshare', 'rm', '-rf', '--', $library)
            $null = Invoke-Probe @('-d', $distro, '-u', $user, '--exec', 'rm', '-rf', '--', $library)
            if (Test-Path -LiteralPath $recipeFolder) { Remove-Item -LiteralPath $recipeFolder -Recurse -Force }
        }
    }

    if ($SavedDelegation) {
        # Saved host Podman delegation from an earlier release: preferences schema 2
        # with podman set. A launch stops before the command; setup from this
        # checkout drops the setting and saves schema 3 preferences. Single quotes
        # only: Windows PowerShell 5.1 passes embedded double quotes to wsl.exe
        # unescaped.
        $backup = $name + '-validate-setup.json'
        $plant = 'import json,os,sys; s,b=sys.argv[1:3]; d=open(s,''rb'').read(); v=json.loads(d); ' +
            'assert v.get(''schema_version'')==3, ''the saved preferences are not schema 3''; ' +
            'f=os.open(b,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); os.write(f,d); os.close(f); ' +
            '[v.pop(k) for k in (''engine_image'',''engine_sources_sha256'',''engine_seccomp_sha256'')]; ' +
            'v.update(schema_version=2,podman=True,delegation_socket=''''); t=s+''.validate''; ' +
            'f=os.open(t,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); ' +
            'os.write(f,(json.dumps(v,indent=2,sort_keys=True)+''\n'').encode()); os.close(f); os.replace(t,s)'
        $migrated = 'import json,sys; v=json.load(open(sys.argv[1])); ' +
            'sys.exit(0 if v.get(''schema_version'')==3 and ''podman'' not in v else 1)'
        # The original goes back into the release it came from, which a completed
        # setup has made the previous one, unless setup removed that release.
        $restore = 'import os,sys; s,b=sys.argv[1:3]; ' +
            'os.replace(b,s) if os.path.isdir(os.path.dirname(s)) else os.remove(b)'
        $resolved = Invoke-Probe @('-d', $distro, '-u', $user, '--cd', '~', '--exec', 'readlink', '-e', '--', $setupFile)
        $savedFile = (@($resolved.Output) -join '').Trim()
        $existing = Invoke-Probe @('-d', $distro, '-u', $user, '--cd', '~', '--exec', 'test', '!', '-e', $backup)
        if ($resolved.Code -ne 0 -or -not $savedFile.StartsWith('/')) {
            Add-Result 'FAIL' 'Saved delegation' ('cannot resolve ' + $setupFile + ' in ' + $distro)
        } elseif ($existing.Code -ne 0) {
            Add-Result 'FAIL' 'Saved delegation' ('~/' + $backup + ' exists in ' + $distro + ' from an earlier run: ' +
                'compare it with ' + $savedFile + ', put it back or remove it, and run the script again')
        } else {
            $planted = Invoke-Probe @('-d', $distro, '-u', $user, '--cd', '~', '--exec', 'python3', '-I', '-c', $plant,
                $savedFile, $backup)
            try {
                if ($planted.Code -ne 0) {
                    Add-Result 'FAIL' 'Saved delegation' ('cannot rewrite ' + $savedFile + ': ' + ($planted.Output -join ' '))
                } else {
                    $r = Invoke-Case '& $E @C -c ''printf ok'''
                    Test-Outcome 'Saved delegation' $r 1 'saved host Podman delegation, which was removed'
                    [Console]::Out.WriteLine('Setup over saved delegation: answer the setup questions as for ' +
                        '--container-setup. It must announce that the saved host Podman delegation was removed.')
                    $process = Start-Process -FilePath $exe -ArgumentList @('-NoProfile', '-File', ('"' + $entry + '"'),
                        '--container-setup') -WorkingDirectory $Checkout -NoNewWindow -Wait -PassThru
                    $check = Invoke-Probe @('-d', $distro, '-u', $user, '--cd', '~', '--exec', 'python3', '-I', '-c',
                        $migrated, $setupFile)
                    if ($process.ExitCode -eq 0 -and $check.Code -eq 0) {
                        Add-Result 'PASS' 'Setup rerun over saved delegation' ('status 0; ' + $setupFile +
                            ' is schema 3 without the podman setting')
                        Test-Outcome 'Launch after the migration' (Invoke-Case '& $E @C -c ''printf ok''') 0 'ok'
                    } else {
                        Add-Result 'FAIL' 'Setup rerun over saved delegation' ('setup status ' + $process.ExitCode +
                            '; preferences check status ' + $check.Code)
                    }
                }
            } finally {
                $null = Invoke-Probe @('-d', $distro, '-u', $user, '--cd', '~', '--exec', 'python3', '-I', '-c', $restore,
                    $savedFile, $backup)
            }
        }
    } else { Add-Result 'SKIP' 'Saved delegation' 'rerun with -SavedDelegation (reruns setup; answer its questions)' }

    if ($Install) {
        . ([IO.Path]::Combine($Checkout, 'launcher', 'windows', 'user-path.ps1'))
        $before = Read-UserPath
        $installedEntry = Join-Path $installFolder ($name + '.ps1')
        try {
            [Console]::Out.WriteLine('Install: answer the setup questions as for --container-setup.')
            $process = Start-Process -FilePath $exe -ArgumentList @('-NoProfile', '-File', ('"' + $entry + '"'),
                '--container-install') -WorkingDirectory $Checkout -NoNewWindow -Wait -PassThru
            $markerFile = Join-Path $installFolder 'install.json'
            $state = ''
            if (Test-Path -LiteralPath $markerFile) { $state = ([IO.File]::ReadAllText($markerFile) | ConvertFrom-Json).state }
            if ($process.ExitCode -eq 0 -and $state -ceq 'complete') {
                Add-Result 'PASS' 'Install from a checkout' ('status 0; ' + $installFolder + ' complete')
            } else {
                Add-Result 'FAIL' 'Install from a checkout' ('status ' + $process.ExitCode + '; install.json state ' + $state)
            }
            $after = Read-UserPath
            $expectedKind = if ($before.Value) { $before.Kind } else { [Microsoft.Win32.RegistryValueKind]::ExpandString }
            if ($after.Value -ceq (Get-PathWithEntry $before.Value $installFolder) -and $after.Kind -eq $expectedKind) {
                Add-Result 'PASS' 'Command on the user PATH (registry)' ('kind ' + $after.Kind + '; other entries unchanged')
            } else {
                Add-Result 'FAIL' 'Command on the user PATH (registry)' ('kind ' + $after.Kind + '; value ' + $after.Value)
            }
            # A new window reads PATH from the registry; so does this child.
            $fresh = '$env:Path = [Environment]::GetEnvironmentVariable(''Path'', ''Machine'') + '';'' + ' +
                '[Environment]::GetEnvironmentVariable(''Path'', ''User''); '
            Test-Outcome 'Command on the user PATH (new window)' (Invoke-Case ($fresh + '& ' + $name + ' @C -c ''printf ok''')) 0 'ok'
            Test-Outcome 'Install from the installed copy' (Invoke-Case ('& ' + (ConvertTo-Literal $installedEntry) +
                ' --container-install')) 1 'this is the installed copy'
            $removed = Invoke-Case ('& ' + (ConvertTo-Literal $installedEntry) + ' --container-uninstall')
            $restored = Read-UserPath
            if ($restored.Value -ceq $before.Value -and ($before.Value -eq '' -or $restored.Kind -eq $before.Kind)) {
                Add-Result 'PASS' 'Uninstall (user PATH)' 'restored to its value before the install'
            } else {
                Add-Result 'FAIL' 'Uninstall (user PATH)' ('value ' + $restored.Value)
            }
            if ($removed.Code -eq 0 -and -not (Test-Path -LiteralPath $installFolder)) {
                Add-Result 'PASS' 'Uninstall (folder)' ('status 0; ' + $installFolder + ' removed')
            } elseif ($removed.Code -eq 1 -and $removed.Err.Contains('wsl --shutdown') -and
                    -not $removed.Err.Contains('did not create')) {
                Add-Result 'PASS' 'Uninstall (folder in use)' ('status 1; reported: ' + (Get-FirstLine $removed.Err))
            } else {
                Add-Result 'FAIL' 'Uninstall' ('status ' + $removed.Code + '; ' + (Get-FirstLine $removed.Err))
            }
        } finally {
            # Whatever failed above, the user PATH loses the entry this run added.
            $now = Read-UserPath
            $cleaned = Get-PathWithoutEntry $now.Value $installFolder
            if ($cleaned -cne $now.Value) {
                [void](Write-UserPath $cleaned $now.Kind)
                [Console]::Out.WriteLine('Removed ' + $installFolder + ' from the user PATH after the run.')
            }
            if (Test-Path -LiteralPath $installFolder) {
                [Console]::Out.WriteLine('Left ' + $installFolder + '; remove it with --container-uninstall from ' +
                    'the checkout.')
            }
        }
    } else { Add-Result 'SKIP' 'Install' 'rerun with -Install (changes the user PATH during the run)' }

    if ($StopMachine) {
        Invoke-DistributionStop
        Test-Outcome 'Stopped machine' (Invoke-Case '& $E @C -c ''printf ok''') 1 'podman machine start'
        Test-Outcome 'Help with a stopped machine' (Invoke-Case '& $E --container-help') 0 'The Podman machine is stopped'
        $running = Invoke-Probe @('-l', '--running', '-q')
        if (@($running.Output | ForEach-Object { $_.Trim() }) -contains $distro) {
            Add-Result 'FAIL' 'Stopped machine stays stopped' ($distro + ' is running after the refusals')
        } else { Add-Result 'PASS' 'Stopped machine stays stopped' ($distro + ' is not running') }
        # Started by wsl.exe alone: no /run/user/<uid>, so no podman command works.
        $null = Invoke-Probe @('-d', $distro, '-u', $user, '--exec', '/bin/true')
        Test-Outcome 'Distribution started by WSL alone (launch)' (Invoke-Case '& $E @C -c ''printf ok''') 1 'wsl --terminate'
        Test-Outcome 'Distribution started by WSL alone (setup)' (Invoke-Case '& $E --container-setup') 1 'runs without the Podman machine'
        Invoke-DistributionStop
        $podman = Get-Command -Name 'podman.exe' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($podman) {
            $started = Invoke-Process $podman.Source ('machine start ' + $distro) $HOME
            if ($started.Code -ne 0) {
                # One retry after a clean stop; WSL may still be settling.
                Invoke-DistributionStop
                Start-Sleep -Seconds 10
                $started = Invoke-Process $podman.Source ('machine start ' + $distro) $HOME
            }
            if ($started.Code -ne 0) {
                Add-Result 'FAIL' 'Machine restarted with Podman' ('podman machine start: status ' + $started.Code + '; ' +
                    (Get-FirstLine $started.Err) + '. Run wsl --shutdown, then podman machine start, before other checks')
            } else {
                Test-Outcome 'Machine restarted with Podman' (Invoke-Case '& $E @C -c ''printf ok''') 0 'ok'
            }
        } else {
            Add-Result 'SKIP' 'Machine restarted with Podman' 'podman.exe not found; start the machine with Podman Desktop'
        }
    } else { Add-Result 'SKIP' 'Stopped machine' 'rerun with -StopMachine (ends running sessions)' }
} finally {
    if ($null -ne $substDrive) { & subst.exe $substDrive /d }
    # After -StopMachine a helper process of WSL or Podman may keep a folder of
    # $work as its current directory; the summary must still be written.
    if (Test-Path -LiteralPath $work) {
        try {
            Remove-Item -LiteralPath $work -Recurse -Force
        } catch {
            $results.Add('Note: ' + $work + ' was not removed (' + $_.Exception.Message + '); remove it after ' +
                'wsl --shutdown or a restart')
            [Console]::Out.WriteLine($results[$results.Count - 1])
        }
    }
    $passed = @($results | Where-Object { $_.StartsWith('RESULT PASS') }).Count
    $failed = @($results | Where-Object { $_.StartsWith('RESULT FAIL') }).Count
    $skipped = @($results | Where-Object { $_.StartsWith('RESULT SKIP') }).Count
    $results.Add(('Summary: {0} passed, {1} failed, {2} skipped' -f $passed, $failed, $skipped))
    $results.Add('By hand: Ctrl+C in an interactive session (one interrupt), closing the window during a session, and')
    $results.Add('  ' + (($name + '.ps1 ' + $shellOption).TrimEnd()) + ' -c ''stty size'' printing the window''s rows and columns; after Ctrl+C and the closed')
    $results.Add('  window, podman ps -a (podman.exe on Windows) must list no container of the session.')
    [IO.File]::WriteAllLines($summaryFile, $results.ToArray())
    foreach ($line in $results.GetRange($results.Count - 4, 4)) { [Console]::Out.WriteLine($line) }
    [Console]::Out.WriteLine('Saved: ' + $summaryFile)
}
