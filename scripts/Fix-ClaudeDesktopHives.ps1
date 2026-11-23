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

.PARAMETER AsSystem
    Internal flag. Do not use directly. The script re-invokes itself with this flag
    via a SYSTEM-level scheduled task to perform the privileged unload.

.PARAMETER Unattended
    Skip all interactive prompts. Running Claude Desktop processes are terminated
    without asking. Never touches Claude Code CLI (claude.exe) processes.

.NOTES
    Requires: Windows 10/11, Administrator elevation.
    The script is safe to run even if no stale hives exist.
#>

param(
    [switch]$AsSystem,
    [switch]$Unattended
)

$ErrorActionPreference = 'Stop'

# -- Hardcoded fallback; auto-detection attempted below --
$PackageFamilyDefault = 'Claude_pzs8sxrjxfjjc'

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
#  SYSTEM PATH - executed inside the scheduled task as SYSTEM
# ==============================================================
if ($AsSystem) {
    $resultDir  = if ($env:CLAUDE_FIX_RESULTDIR) { $env:CLAUDE_FIX_RESULTDIR } else { $env:TEMP }
    $resultFile = Join-Path $resultDir 'claude_hive_fix_result.json'
    $packageFamilyPattern = if ($env:CLAUDE_FIX_PKGFAMILY) { $env:CLAUDE_FIX_PKGFAMILY } else { $PackageFamilyDefault }
    $hivePattern = Get-HiveMatchPattern $packageFamilyPattern

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
    Set-Content -Path $resultFile -Value $json -Encoding UTF8
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

$scriptPath = $MyInvocation.MyCommand.Path
if (-not $scriptPath) {
    Write-Host '       ERROR: Cannot determine script path.' -ForegroundColor Red
    Write-Host '       Please save and run this as a .ps1 file (not pasted into a console).' -ForegroundColor Yellow
    Pause-IfInteractive
    exit 1
}

$taskName   = "ClaudeHiveFix_$(Get-Random -Minimum 10000 -Maximum 99999)"
$resultFile = Join-Path $env:TEMP 'claude_hive_fix_result.json'
if (Test-Path $resultFile) { Remove-Item $resultFile -Force }

$wrapperPath = Join-Path $env:TEMP 'claude_hive_fix_wrapper.ps1'
@"
`$env:CLAUDE_FIX_RESULTDIR  = '$($env:TEMP -replace "'","''")'
`$env:CLAUDE_FIX_PKGFAMILY  = '$($PackageFamily -replace "'","''")'
& '$($scriptPath -replace "'","''")' -AsSystem
"@ | Set-Content -Path $wrapperPath -Encoding UTF8

try {
    $action    = New-ScheduledTaskAction -Execute 'powershell.exe' `
                    -Argument "-ExecutionPolicy Bypass -NoProfile -NonInteractive -File `"$wrapperPath`""
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    $settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

    Register-ScheduledTask -TaskName $taskName -Action $action `
        -Principal $principal -Settings $settings -Force | Out-Null

    Start-ScheduledTask -TaskName $taskName

    $elapsed = 0
    while ($elapsed -lt 30) {
        Start-Sleep -Seconds 1
        $elapsed++
        $state = (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue).State
        if ($state -ne 'Running') { break }
    }

    if ($elapsed -ge 30) {
        Write-Host '       WARNING: Scheduled task timed out after 30 s.' -ForegroundColor Red
    } else {
        Write-Host "       Task completed in ${elapsed}s." -ForegroundColor DarkGray
    }
}
catch {
    Write-Host "       ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Pause-IfInteractive
    exit 1
}
finally {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Remove-Item $wrapperPath -Force -ErrorAction SilentlyContinue
}

# -- Parse results --
if (-not (Test-Path $resultFile)) {
    Write-Host '       ERROR: Result file not found. The SYSTEM task may have failed.' -ForegroundColor Red
    Write-Host '       Fallback: reboot your PC to clear the stale hives.' -ForegroundColor Yellow
    Pause-IfInteractive
    exit 1
}

$raw = Get-Content $resultFile -Raw
Remove-Item $resultFile -Force -ErrorAction SilentlyContinue

$results = @()
if ($raw -and $raw.Trim()) {
    # PS 5.1: ConvertFrom-Json emits a JSON array as ONE pipeline item.
    # Assign first, then wrap - piping into @() would nest it.
    try {
        $parsed  = ConvertFrom-Json -InputObject $raw
        $results = @($parsed)
    } catch { $results = @() }
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
