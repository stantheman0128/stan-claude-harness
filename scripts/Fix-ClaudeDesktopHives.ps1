<#
.SYNOPSIS
    Fixes Claude Desktop launch failure caused by stale Desktop Bridge container registry hives.

.DESCRIPTION
    When Claude Desktop crashes or closes abnormally, its Desktop AppX container hives
    can remain mounted in HKLM\SYSTEM\CurrentControlSet\Control\hivelist. These stale
    \REGISTRY\WC\Silo* entries cause ERROR_SHARING_VIOLATION (0x80070020) on every
    subsequent launch attempt, with Events 208/215 in AppModel-Runtime/Admin.

    This script:
      1. Detects stale Silo hives referencing the Claude package family
      2. Escalates to SYSTEM via a one-shot scheduled task
      3. Force-unloads the hives using NtUnloadKey2(..., REG_FORCE_UNLOAD)
      4. Verifies the registry is clean

    No reboot required.

    Reference: https://github.com/anthropics/claude-code/issues/42776

.PARAMETER Unattended
    Skip all interactive prompts. Running Claude Desktop processes are terminated
    without asking. Never touches Claude Code CLI (claude.exe) processes.

.NOTES
    Requires: Windows 10/11, Administrator elevation.
    The script is safe to run even if no stale hives exist.
    This file never runs as SYSTEM. The SYSTEM step runs a generated payload from
    a temporary admin-only folder under ProgramData, after a SHA-256 check.
#>

param(
    [switch]$Unattended
)

$ErrorActionPreference = 'Stop'

# -- Hardcoded fallback; auto-detection attempted below --
$PackageFamilyDefault = 'Claude_pzs8sxrjxfjjc'

# Strict shapes for the values handed to the SYSTEM task, checked on both sides.
# Package family = Name (3-50 of A-Z a-z 0-9 . -) + '_' + 13-char publisher ID.
# \z, not $: in .NET regex $ also matches before a trailing newline.
$PackageFamilyRegex = '^[A-Za-z0-9.\-]{3,50}_[0-9a-hjkmnp-tv-z]{13}\z'
$WorkDirRegex       = '^[A-Za-z]:\\ProgramData\\ClaudeHiveFix_[0-9a-f]{32}\z'

# Hive file paths reference the package in two different forms:
#   ...\Packages\Claude_pzs8sxrjxfjjc\...                    (family name)
#   ...\WindowsApps\Claude_1.32885.1.0_x64__pzs8sxrjxfjjc\...  (full package name)
# Build a wildcard that catches both: *Claude_*pzs8sxrjxfjjc*
function Get-HiveMatchPattern {
    param([string]$PackageFamilyName)
    $parts = $PackageFamilyName -split '_'
    if ($parts.Count -ge 2) {
        return "*$($parts[0])_*$($parts[-1])*"
    }
    return "*$PackageFamilyName*"
}

# ==============================================================
#  HELPERS for the SYSTEM hand-off (step 4)
# ==============================================================

# True only for a real folder (no reparse point) owned by SYSTEM or
# Administrators, with inheritance off and ACEs for those two only.
# Self-contained: step 4 copies this function into the SYSTEM payload.
function Test-AdminOnlyDirectory {
    param([string]$Path)
    $admins = @('S-1-5-18', 'S-1-5-32-544')
    try {
        $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
        $acl  = $item.GetAccessControl()
    } catch { return $false }
    if (-not $item.PSIsContainer) { return $false }
    if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { return $false }
    if ($admins -notcontains $acl.GetOwner([System.Security.Principal.SecurityIdentifier]).Value) { return $false }
    if (-not $acl.AreAccessRulesProtected) { return $false }
    foreach ($rule in $acl.GetAccessRules($true, $true, [System.Security.Principal.SecurityIdentifier])) {
        if ($admins -notcontains $rule.IdentityReference.Value) { return $false }
    }
    return $true
}

# The work folder's parent must stop non-admins from deleting or renaming
# entries in it (which would let them swap our folder) and from changing
# its own ACL or owner. Creating new entries there is fine.
function Assert-SafeParentDirectory {
    param([string]$Path)
    $trusted = @('S-1-5-18', 'S-1-5-32-544',
                 'S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')  # TrustedInstaller
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if (-not $item.PSIsContainer -or ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
        throw "Not a plain folder: $Path"
    }
    $acl = $item.GetAccessControl()
    if ($trusted -notcontains $acl.GetOwner([System.Security.Principal.SecurityIdentifier]).Value) {
        throw "Unexpected owner on $Path"
    }
    # DELETE | FILE_DELETE_CHILD | WRITE_DAC | WRITE_OWNER | GENERIC_ALL
    $dangerous = 0x00010000 -bor 0x00000040 -bor 0x00040000 -bor 0x00080000 -bor 0x10000000
    foreach ($rule in $acl.GetAccessRules($true, $true, [System.Security.Principal.SecurityIdentifier])) {
        if ($rule.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow) { continue }
        if ($rule.PropagationFlags -band [System.Security.AccessControl.PropagationFlags]::InheritOnly) { continue }
        if ($trusted -contains $rule.IdentityReference.Value) { continue }
        if ([int]$rule.FileSystemRights -band $dangerous) {
            throw "$Path lets $($rule.IdentityReference.Value) delete or re-permission its entries"
        }
    }
}

# Owner Administrators, inheritance off, SYSTEM and Administrators full control.
function Set-AdminOnlyRules {
    param($Security, [System.Security.AccessControl.InheritanceFlags]$Inherit)
    $Security.SetOwner([System.Security.Principal.SecurityIdentifier]'S-1-5-32-544')
    $Security.SetAccessRuleProtection($true, $false)
    foreach ($sid in 'S-1-5-18', 'S-1-5-32-544') {
        $Security.AddAccessRule([System.Security.AccessControl.FileSystemAccessRule]::new(
            [System.Security.Principal.SecurityIdentifier]$sid,
            [System.Security.AccessControl.FileSystemRights]::FullControl, $Inherit,
            [System.Security.AccessControl.PropagationFlags]::None,
            [System.Security.AccessControl.AccessControlType]::Allow))
    }
}

function New-AdminOnlyDirectory {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path) { throw "Work folder already exists: $Path" }
    $sec = New-Object System.Security.AccessControl.DirectorySecurity
    Set-AdminOnlyRules $sec ([System.Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit')
    # The ACL is applied at creation, so there is no window with the inherited
    # ProgramData ACL (which lets Users create files in new subfolders).
    [void][System.IO.Directory]::CreateDirectory($Path, $sec)
    if (-not (Test-AdminOnlyDirectory $Path) -or @(Get-ChildItem -LiteralPath $Path -Force).Count -ne 0) {
        throw "Work folder failed its security check: $Path"
    }
}

function Write-AdminOnlyFile {
    param([string]$Path, [byte[]]$Bytes)
    $sec = New-Object System.Security.AccessControl.FileSecurity
    Set-AdminOnlyRules $sec ([System.Security.AccessControl.InheritanceFlags]::None)
    # CreateNew: never write through a file or link that is already there.
    $fs = [System.IO.FileStream]::new($Path, [System.IO.FileMode]::CreateNew,
        [System.Security.AccessControl.FileSystemRights]::Write, [System.IO.FileShare]::None,
        4096, [System.IO.FileOptions]::None, $sec)
    try { $fs.Write($Bytes, 0, $Bytes.Length) } finally { $fs.Dispose() }
}

# Single-quotes a value for the generated SYSTEM code. Rejects rather than
# escapes: a quote or anything outside printable ASCII fails, which also
# covers the Unicode quotes (U+2018..U+201B) PowerShell treats as quotes.
function ConvertTo-PSLiteral {
    param([string]$Value)
    if ($Value -cnotmatch '^[\x20-\x26\x28-\x7E]*\z') {
        throw 'Refusing to embed a value with quotes or non-ASCII characters.'
    }
    return "'" + $Value + "'"
}

function Get-Sha256Hex {
    param([byte[]]$Bytes)
    $sha = New-Object System.Security.Cryptography.SHA256CryptoServiceProvider
    try { return -join ($sha.ComputeHash($Bytes) | ForEach-Object { $_.ToString('x2') }) }
    finally { $sha.Dispose() }
}

# ==============================================================
#  C# INTEROP: NtUnloadKey2 + Privilege Adjustment
# ==============================================================
$CSharpCode = @'
using System;
using System.Runtime.InteropServices;

public static class HiveUnloader
{
    [DllImport("ntdll.dll")]
    private static extern int NtUnloadKey2(
        ref OBJECT_ATTRIBUTES KeyObjectAttributes, uint Flags);

    private const uint REG_FORCE_UNLOAD    = 1;
    private const uint OBJ_CASE_INSENSITIVE = 0x00000040;

    [StructLayout(LayoutKind.Sequential)]
    private struct UNICODE_STRING
    {
        public ushort Length;
        public ushort MaximumLength;
        public IntPtr Buffer;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct OBJECT_ATTRIBUTES
    {
        public int    Length;
        public IntPtr RootDirectory;
        public IntPtr ObjectName;
        public uint   Attributes;
        public IntPtr SecurityDescriptor;
        public IntPtr SecurityQualityOfService;
    }

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool OpenProcessToken(
        IntPtr ProcessHandle, uint Access, out IntPtr TokenHandle);

    [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern bool LookupPrivilegeValue(
        string lpSystemName, string lpName, out LUID lpLuid);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool AdjustTokenPrivileges(
        IntPtr TokenHandle, bool DisableAll,
        ref TOKEN_PRIVILEGES NewState, uint BufLen,
        IntPtr PrevState, IntPtr RetLen);

    [DllImport("kernel32.dll")]
    private static extern IntPtr GetCurrentProcess();

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool CloseHandle(IntPtr handle);

    [StructLayout(LayoutKind.Sequential)]
    private struct LUID
    {
        public uint LowPart;
        public int  HighPart;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct LUID_AND_ATTRIBUTES
    {
        public LUID Luid;
        public uint Attributes;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct TOKEN_PRIVILEGES
    {
        public uint                PrivilegeCount;
        public LUID_AND_ATTRIBUTES Privilege;
    }

    private const uint TOKEN_ADJUST_PRIVILEGES = 0x0020;
    private const uint TOKEN_QUERY             = 0x0008;
    private const uint SE_PRIVILEGE_ENABLED    = 0x00000002;

    public static bool EnablePrivilege(string privilegeName)
    {
        IntPtr token;
        if (!OpenProcessToken(GetCurrentProcess(),
                TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, out token))
            return false;

        try
        {
            LUID luid;
            if (!LookupPrivilegeValue(null, privilegeName, out luid))
                return false;

            TOKEN_PRIVILEGES tp = new TOKEN_PRIVILEGES();
            tp.PrivilegeCount       = 1;
            tp.Privilege.Luid       = luid;
            tp.Privilege.Attributes = SE_PRIVILEGE_ENABLED;

            return AdjustTokenPrivileges(token, false, ref tp, 0,
                                         IntPtr.Zero, IntPtr.Zero);
        }
        finally { CloseHandle(token); }
    }

    public static int ForceUnloadHive(string ntRegistryPath)
    {
        IntPtr usPtr  = Marshal.AllocHGlobal(
                            Marshal.SizeOf(typeof(UNICODE_STRING)));
        IntPtr strBuf = Marshal.StringToHGlobalUni(ntRegistryPath);

        try
        {
            var us           = new UNICODE_STRING();
            us.Length        = (ushort)(ntRegistryPath.Length * 2);
            us.MaximumLength = (ushort)(us.Length + 2);
            us.Buffer        = strBuf;
            Marshal.StructureToPtr(us, usPtr, false);

            var oa = new OBJECT_ATTRIBUTES();
            oa.Length                    = Marshal.SizeOf(typeof(OBJECT_ATTRIBUTES));
            oa.RootDirectory             = IntPtr.Zero;
            oa.ObjectName                = usPtr;
            oa.Attributes                = OBJ_CASE_INSENSITIVE;
            oa.SecurityDescriptor        = IntPtr.Zero;
            oa.SecurityQualityOfService  = IntPtr.Zero;

            return NtUnloadKey2(ref oa, REG_FORCE_UNLOAD);
        }
        finally
        {
            Marshal.FreeHGlobal(strBuf);
            Marshal.FreeHGlobal(usPtr);
        }
    }
}
'@


# ==============================================================
#  SYSTEM SIDE - code run by the one-shot SYSTEM scheduled task
# ==============================================================
# The admin process never runs this block. Step 4 writes its text, with
# validated values baked in, to a fresh admin-only folder under ProgramData,
# and the task checks that file's SHA-256 before running it. It reads no
# environment variables and writes only inside that folder.
$SystemSideScript = {
    $ErrorActionPreference = 'Stop'

    # Fail closed: re-check the baked-in values and the folder before writing.
    if ($PackageFamilyName -cnotmatch $PackageFamilyRegex -or
        $WorkDir -cnotmatch $WorkDirRegex -or
        -not (Test-AdminOnlyDirectory $WorkDir)) {
        exit 2
    }

    # CreateNew refuses anything already at the path. While this handle is
    # open the folder cannot be deleted, and the final write goes through the
    # handle, so the path is not resolved again. The second check catches a
    # folder swapped between the first check and the open.
    $resultStream = [System.IO.FileStream]::new(
        (Join-Path $WorkDir 'result.json'), [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    if (-not (Test-AdminOnlyDirectory $WorkDir)) { $resultStream.Dispose(); exit 2 }

    # Add-Type runs csc.exe, which writes temp files under %TMP%. For SYSTEM
    # that is C:\Windows\Temp, where non-admin users can create files.
    $env:TMP  = $WorkDir
    $env:TEMP = $WorkDir

    $hivePattern = Get-HiveMatchPattern $PackageFamilyName

    $results = @()

    try {
        Add-Type -TypeDefinition $CSharpCode -Language CSharp

        [HiveUnloader]::EnablePrivilege('SeRestorePrivilege') | Out-Null
        [HiveUnloader]::EnablePrivilege('SeBackupPrivilege')  | Out-Null

        $hlKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey(
                     'SYSTEM\CurrentControlSet\Control\hivelist', $false)

        if ($hlKey) {
            foreach ($vn in $hlKey.GetValueNames()) {
                if ($vn -like '*\REGISTRY\WC\Silo*') {
                    $fileData = [string]$hlKey.GetValue($vn)
                    if ($fileData -and $fileData -like $hivePattern) {
                        # NTSTATUS is a signed Int32; error codes are negative.
                        # Format directly - casting to [uint32] throws on negatives.
                        try {
                            $ntstatus = [HiveUnloader]::ForceUnloadHive($vn)
                            $results += [pscustomobject]@{
                                HivePath = $vn
                                FilePath = $fileData
                                NtStatus = '0x{0:X8}' -f $ntstatus
                                Success  = ($ntstatus -eq 0)
                                Error    = $null
                            }
                        }
                        catch {
                            # One hive failing must not abort the remaining unloads.
                            $results += [pscustomobject]@{
                                HivePath = $vn
                                FilePath = $fileData
                                NtStatus = 'EXCEPTION'
                                Success  = $false
                                Error    = $_.Exception.Message
                            }
                        }
                    }
                }
            }
            $hlKey.Close()
        }
    }
    catch {
        $results += [pscustomobject]@{
            HivePath = 'N/A'
            FilePath = 'N/A'
            NtStatus = 'EXCEPTION'
            Success  = $false
            Error    = $_.Exception.Message
        }
    }

    # Always emit a JSON array, even when empty, so the parent can parse it.
    $json = if ($results.Count -eq 0) { '[]' }
            else { ConvertTo-Json -InputObject @($results) -Depth 3 }
    # UTF-8 with BOM plus a trailing newline, as Set-Content -Encoding UTF8 wrote.
    $writer = [System.IO.StreamWriter]::new($resultStream, [System.Text.UTF8Encoding]::new($true))
    try { $writer.WriteLine($json) } finally { $writer.Dispose() }
    exit 0
}


# ==============================================================
#  ADMIN PATH - user-facing interactive flow
# ==============================================================

function Pause-IfInteractive {
    param([string]$Message = 'Press Enter to exit')
    if (-not $Unattended) { Read-Host $Message | Out-Null }
}

$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host ''
    Write-Host '[ERROR] This script must be run as Administrator.' -ForegroundColor Red
    Write-Host '        Right-click the .bat launcher and choose "Run as administrator".' -ForegroundColor Yellow
    Write-Host ''
    Pause-IfInteractive
    exit 1
}

Write-Host ''
Write-Host '  ================================================================' -ForegroundColor Cyan
Write-Host '    Claude Desktop Launch Fix  -  Stale Container Hive Cleanup    ' -ForegroundColor White
Write-Host '  ================================================================' -ForegroundColor Cyan
Write-Host '  Ref: github.com/anthropics/claude-code/issues/42776'             -ForegroundColor DarkGray
Write-Host ''

# -- 1. Auto-detect Claude package family --
Write-Host '[1/5] Detecting Claude Desktop package...' -ForegroundColor Yellow
$PackageFamily = $PackageFamilyDefault
try {
    $pkg = Get-AppxPackage -Name '*Claude*' -ErrorAction SilentlyContinue |
           Select-Object -First 1
    if ($pkg) {
        $PackageFamily = $pkg.PackageFamilyName
        Write-Host "       Found: $($pkg.Name) v$($pkg.Version)" -ForegroundColor Green
        Write-Host "       Family: $PackageFamily" -ForegroundColor DarkGray
    } else {
        Write-Host "       Package not found via Get-AppxPackage; using default: $PackageFamily" -ForegroundColor DarkYellow
    }
}
catch {
    Write-Host "       Detection failed; using default: $PackageFamily" -ForegroundColor DarkYellow
}

# -- 2. Check for running Claude DESKTOP processes --
#    Must NOT match Claude Code CLI (claude.exe under ~\.local\bin or similar).
#    Only packaged Desktop Bridge processes living under WindowsApps count.
Write-Host '[2/5] Checking for running Claude Desktop processes...' -ForegroundColor Yellow
$allClaude = @(Get-Process -Name 'Claude*' -ErrorAction SilentlyContinue)
$claudeProcs = @()
$skipped     = @()
foreach ($p in $allClaude) {
    $path = $null
    try { $path = $p.Path } catch { $path = $null }
    if ($path -and ($path -like '*\WindowsApps\*' -or $path -like "*$PackageFamily*")) {
        $claudeProcs += $p
    } else {
        $skipped += $p
    }
}
if ($skipped.Count -gt 0) {
    Write-Host "       Ignoring $($skipped.Count) non-Desktop process(es) (Claude Code CLI etc.):" -ForegroundColor DarkGray
    $skipped | ForEach-Object {
        Write-Host "         - $($_.ProcessName) (PID $($_.Id))  $($_.Path)" -ForegroundColor DarkGray
    }
}

if ($claudeProcs.Count -gt 0) {
    Write-Host '       WARNING - Found running Claude Desktop processes:' -ForegroundColor Red
    $claudeProcs | ForEach-Object {
        Write-Host "         - $($_.ProcessName) (PID $($_.Id))  $($_.Path)" -ForegroundColor Red
    }
    Write-Host ''
    $answer = if ($Unattended) { 'Y' } else { Read-Host '       Kill them and continue? (Y/N)' }
    if ($answer -match '^[Yy]') {
        $claudeProcs | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        Write-Host '       Processes terminated.' -ForegroundColor Green
    } else {
        Write-Host '       Aborted. Close Claude Desktop first, then re-run.' -ForegroundColor Yellow
        Pause-IfInteractive
        exit 0
    }
} else {
    Write-Host '       No Claude Desktop processes running. Good.' -ForegroundColor Green
}

# -- 3. Scan for stale hives --
Write-Host '[3/5] Scanning hivelist for stale container hives...' -ForegroundColor Yellow
$HivePattern = Get-HiveMatchPattern $PackageFamily
Write-Host "       Match pattern: $HivePattern" -ForegroundColor DarkGray
$staleHives = @()
try {
    $hlKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey(
                 'SYSTEM\CurrentControlSet\Control\hivelist', $false)
    if ($hlKey) {
        foreach ($vn in $hlKey.GetValueNames()) {
            if ($vn -like '*\REGISTRY\WC\Silo*') {
                $fileData = [string]$hlKey.GetValue($vn)
                if ($fileData -and $fileData -like $HivePattern) {
                    $staleHives += [pscustomobject]@{ Name = $vn; File = $fileData }
                }
            }
        }
        $hlKey.Close()
    }
}
catch {
    Write-Host "       ERROR reading hivelist: $($_.Exception.Message)" -ForegroundColor Red
    Pause-IfInteractive
    exit 1
}

if ($staleHives.Count -eq 0) {
    Write-Host '       No stale Claude container hives found.' -ForegroundColor Green
    Write-Host ''
    Write-Host '  Registry is clean. If Claude still will not launch, try:' -ForegroundColor Gray
    Write-Host '    - Settings > Apps > Claude > Advanced options > Reset' -ForegroundColor Gray
    Write-Host '    - Uninstall and reinstall Claude Desktop' -ForegroundColor Gray
    Write-Host ''
    Pause-IfInteractive
    exit 0
}

Write-Host "       Found $($staleHives.Count) stale hive(s):" -ForegroundColor Red
foreach ($h in $staleHives) {
    $short = if ($h.Name -match 'Silo([a-f0-9]{8})') {
        "Silo$($Matches[1])..."
    } else {
        $h.Name.Substring(0, [Math]::Min(50, $h.Name.Length)) + '...'
    }
    $leaf = Split-Path $h.File -Leaf
    Write-Host "         $short  ->  $leaf" -ForegroundColor DarkYellow
}

# -- 4. Force-unload via SYSTEM scheduled task --
Write-Host ''
Write-Host '[4/5] Force-unloading stale hives (escalating to SYSTEM)...' -ForegroundColor Yellow

# Everything the SYSTEM task runs or writes lives in a fresh admin-only folder
# under ProgramData. The task itself carries only a short stub that checks the
# payload's SHA-256 before running it. Paths come from GetSystemDirectory, not
# from environment variables: an elevated process inherits HKCU\Environment,
# which the non-elevated user can edit.
$taskName       = 'ClaudeHiveFix_' + [guid]::NewGuid().ToString('N')
$taskAttempted  = $false
$step4Failed    = $false
$workDir        = $null
$workDirCreated = $false
$resultFound    = $false
$raw            = $null

try {
    if ($PackageFamily -cnotmatch $PackageFamilyRegex) {
        throw "Unexpected package family name format; refusing to pass it to SYSTEM: $PackageFamily"
    }

    $systemDir   = [System.Environment]::SystemDirectory
    $programData = Join-Path ([System.IO.Path]::GetPathRoot($systemDir)) 'ProgramData'
    Assert-SafeParentDirectory $programData

    $workDir = Join-Path $programData ('ClaudeHiveFix_' + [guid]::NewGuid().ToString('N'))
    if ($workDir -cnotmatch $WorkDirRegex) { throw "Unexpected work folder path: $workDir" }
    New-AdminOnlyDirectory $workDir
    $workDirCreated = $true
    $payloadFile = Join-Path $workDir 'payload.ps1'
    $resultFile  = Join-Path $workDir 'result.json'

    # Per-run secret inside the payload: nobody who cannot read this folder can
    # rebuild a file with the same hash, so a planted copy fails the stub check.
    $nonceBytes = New-Object byte[] 16
    $rng = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
    try { $rng.GetBytes($nonceBytes) } finally { $rng.Dispose() }
    $nonce = -join ($nonceBytes | ForEach-Object { $_.ToString('x2') })

    $cSharpB64   = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($CSharpCode))
    $payloadText = @(
        '# Generated by Fix-ClaudeDesktopHives.ps1. Runs once as SYSTEM, then deleted.'
        '$RunNonce = ' + (ConvertTo-PSLiteral $nonce)
        '$PackageFamilyRegex = ' + (ConvertTo-PSLiteral $PackageFamilyRegex)
        '$WorkDirRegex = ' + (ConvertTo-PSLiteral $WorkDirRegex)
        '$PackageFamilyName = ' + (ConvertTo-PSLiteral $PackageFamily)
        '$WorkDir = ' + (ConvertTo-PSLiteral $workDir)
        '$CSharpCode = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String(' +
            (ConvertTo-PSLiteral $cSharpB64) + '))'
        'function Get-HiveMatchPattern {' + ${function:Get-HiveMatchPattern}.ToString() + '}'
        'function Test-AdminOnlyDirectory {' + ${function:Test-AdminOnlyDirectory}.ToString() + '}'
        $SystemSideScript.ToString()
    ) -join "`n"
    $payloadBytes = [System.Text.Encoding]::UTF8.GetBytes($payloadText)
    $payloadHash  = Get-Sha256Hex $payloadBytes
    Write-AdminOnlyFile $payloadFile $payloadBytes

    # The stub runs the exact bytes it hashed, so there is no gap between
    # check and use. -EncodedCommand also keeps execution policy out of it.
    $stub = @(
        '$ErrorActionPreference = ''Stop'''
        '$b = [System.IO.File]::ReadAllBytes(' + (ConvertTo-PSLiteral $payloadFile) + ')'
        '$s = New-Object System.Security.Cryptography.SHA256CryptoServiceProvider'
        '$h = -join ($s.ComputeHash($b) | ForEach-Object { $_.ToString(''x2'') })'
        'if ($h -cne ' + (ConvertTo-PSLiteral $payloadHash) + ') { exit 3 }'
        '& ([scriptblock]::Create([System.Text.Encoding]::UTF8.GetString($b)))'
    ) -join "`n"
    $encoded = [System.Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($stub))
    $psExe   = Join-Path $systemDir 'WindowsPowerShell\v1.0\powershell.exe'

    $action    = New-ScheduledTaskAction -Execute $psExe `
                    -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand $encoded"
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    $settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

    # No -Force: never take over an existing task with this name. The flag is
    # set first so a registration that fails halfway is still cleaned up.
    $taskAttempted = $true
    Register-ScheduledTask -TaskName $taskName -TaskPath '\' -Action $action `
        -Principal $principal -Settings $settings | Out-Null

    # Last check right before SYSTEM starts: folder still admin-only, payload unchanged.
    if (-not (Test-AdminOnlyDirectory $workDir)) { throw "Work folder is no longer admin-only: $workDir" }
    if ((Get-Sha256Hex ([System.IO.File]::ReadAllBytes($payloadFile))) -cne $payloadHash) {
        throw 'Payload changed before the SYSTEM task started; aborting.'
    }

    Start-ScheduledTask -TaskName $taskName -TaskPath '\'

    $elapsed = 0
    while ($elapsed -lt 30) {
        Start-Sleep -Seconds 1
        $elapsed++
        $state = (Get-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction SilentlyContinue).State
        if ($state -ne 'Running') { break }
    }

    if ($elapsed -ge 30) {
        Write-Host '       WARNING: Scheduled task timed out after 30 s.' -ForegroundColor Red
    } else {
        Write-Host "       Task completed in ${elapsed}s." -ForegroundColor DarkGray
    }

    # Read the result here; the finally block deletes the folder.
    if (Test-Path -LiteralPath $resultFile) {
        try {
            $raw = Get-Content -LiteralPath $resultFile -Raw
            $resultFound = $true
        } catch { $resultFound = $false }
    }
}
catch {
    Write-Host "       ERROR: $($_.Exception.Message)" -ForegroundColor Red
    $step4Failed = $true
}
finally {
    # Disable first so no new instance can start, stop any running one and
    # wait for it, then delete the task. Only then is the folder safe to
    # delete: a SYSTEM process still running could otherwise follow the path
    # to a folder a user re-created after the delete. Any doubt keeps the folder.
    $taskStopped = $true
    $taskGone    = $true
    if ($taskAttempted) {
        $taskStopped = $false
        $taskGone    = $false
        try { Disable-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction SilentlyContinue | Out-Null } catch {}
        try { Stop-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction SilentlyContinue } catch {}
        try {
            for ($i = 0; $i -lt 10; $i++) {
                $t = Get-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction SilentlyContinue
                if (-not $t -or $t.State -ne 'Running') { $taskStopped = $true; break }
                Start-Sleep -Seconds 1
            }
        } catch {}
        try { Unregister-ScheduledTask -TaskName $taskName -TaskPath '\' -Confirm:$false -ErrorAction SilentlyContinue } catch {}
        try { $taskGone = -not (Get-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction SilentlyContinue) } catch {}
    }
    if ($workDirCreated) {
        if ($taskStopped -and $taskGone) {
            # .NET's recursive delete removes reparse points without following them.
            try { [System.IO.Directory]::Delete($workDir, $true) }
            catch { Write-Host "       WARNING: Could not delete $workDir : $($_.Exception.Message)" -ForegroundColor DarkYellow }
        } else {
            Write-Host "       WARNING: SYSTEM task not confirmed stopped; leaving admin-only folder $workDir" -ForegroundColor DarkYellow
        }
    } elseif ($workDir -and (Test-Path -LiteralPath $workDir)) {
        # It failed its security check, so it may not be ours: keep it, but say where it is.
        Write-Host "       WARNING: Left $workDir in place (failed its security check). Inspect it and delete it by hand." -ForegroundColor DarkYellow
    }
}
# Pause only after cleanup, so the task and folder never wait on the prompt.
if ($step4Failed) {
    Pause-IfInteractive
    exit 1
}

# -- Parse results --
if (-not $resultFound) {
    Write-Host '       ERROR: Result file not found. The SYSTEM task may have failed.' -ForegroundColor Red
    Write-Host '       Fallback: reboot your PC to clear the stale hives.' -ForegroundColor Yellow
    Pause-IfInteractive
    exit 1
}

$results  = @()
$parsedOk = $false
if ($raw -and $raw.Trim()) {
    # PS 5.1: ConvertFrom-Json emits a JSON array as ONE pipeline item.
    # Assign first, then wrap - piping into @() would nest it.
    try {
        $parsed  = ConvertFrom-Json -InputObject $raw
        $results = @($parsed)
        $parsedOk = ($null -ne $parsed)
    } catch { $results = @() }
}

# A clean run always writes a JSON array ("[]" when there is nothing to
# unload). An empty or unparsable file means the SYSTEM side stopped after
# creating it, so treat it like a missing file.
if (-not $parsedOk) {
    Write-Host '       ERROR: Result file is empty or unreadable. The SYSTEM task may have failed.' -ForegroundColor Red
    Write-Host '       Fallback: reboot your PC to clear the stale hives.' -ForegroundColor Yellow
    Pause-IfInteractive
    exit 1
}

if ($results.Count -eq 0) {
    Write-Host '       SYSTEM task reported no hives to unload.' -ForegroundColor Yellow
}

$okCount   = @($results | Where-Object { $_.Success -eq $true }).Count
$failCount = @($results | Where-Object { $_.Success -ne $true }).Count

Write-Host ''
foreach ($r in $results) {
    $icon  = if ($r.Success) { 'OK  ' } else { 'FAIL' }
    $color = if ($r.Success) { 'Green' } else { 'Red' }
    $short = if ($r.HivePath -match 'Silo([a-f0-9]{8})') {
        "Silo$($Matches[1])..."
    } else { $r.HivePath }
    Write-Host "       [$icon]  $short   NTSTATUS=$($r.NtStatus)" -ForegroundColor $color
    if ($r.Error) {
        Write-Host "              Exception: $($r.Error)" -ForegroundColor DarkRed
    }
}

Write-Host ''
if ($failCount -gt 0 -and $okCount -gt 0) {
    Write-Host "       $okCount unloaded successfully, $failCount failed." -ForegroundColor Yellow
    Write-Host '       Failed hives (typically COM cache) are usually non-blocking.' -ForegroundColor DarkYellow
    Write-Host '       Claude Desktop should still launch - try it now.' -ForegroundColor Cyan
}
elseif ($failCount -gt 0 -and $okCount -eq 0) {
    Write-Host "       All $failCount hive(s) failed to unload." -ForegroundColor Red
    Write-Host '       A reboot is needed to clear them.' -ForegroundColor Yellow
}
elseif ($okCount -gt 0) {
    Write-Host "       All $okCount hive(s) unloaded successfully!" -ForegroundColor Green
}

# -- 5. Verify --
Write-Host ''
Write-Host '[5/5] Verifying registry is clean...' -ForegroundColor Yellow
$remaining = 0
try {
    $hlKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey(
                 'SYSTEM\CurrentControlSet\Control\hivelist', $false)
    if ($hlKey) {
        foreach ($vn in $hlKey.GetValueNames()) {
            if ($vn -like '*\REGISTRY\WC\Silo*') {
                $fd = [string]$hlKey.GetValue($vn)
                if ($fd -and $fd -like $HivePattern) { $remaining++ }
            }
        }
        $hlKey.Close()
    }
}
catch {}

if ($remaining -eq 0) {
    Write-Host '       Registry is clean - all stale hives removed.' -ForegroundColor Green
} else {
    Write-Host "       $remaining hive(s) still present (locked by kernel)." -ForegroundColor Yellow
    Write-Host '       These will clear on reboot, but Claude may still launch.' -ForegroundColor DarkYellow
}

Write-Host ''
Write-Host '  ================================================================' -ForegroundColor Cyan
Write-Host '    Done!  Try launching Claude Desktop now.                       ' -ForegroundColor White
Write-Host '  ================================================================' -ForegroundColor Cyan
Write-Host ''
Pause-IfInteractive
