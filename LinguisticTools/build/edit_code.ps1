# vim: set filetype=conf :
#------------------------------------------------------------------------------
#
# Created June 25 2015 by Jim K
#
# 17-Aug-15 JDK  Recursively open files to handle subdirectories.
# 05-Nov-15 JDK  Module names should be lowercase.
# 29-Jan-16 JDK  Use relative paths to work on dev machine.
#
# Opens all testing code for editing using a text editor, with each package in
# a separate window.
# Specify -tests to edit tests instead of the main code.
# Useful when run with a windows shortcut.
#
#------------------------------------------------------------------------------
param ([switch]$tests)
$block = {
    Param($psscriptroot, $subpath, [bool]$editTests)
    #$EDITOR = "${Env:ProgramFiles(x86)}\Vim\vim80\gvim.exe"
    $EDITOR = "${Env:ProgramFiles}\Vim\vim91\gvim.exe"
    $inpath = "$psscriptroot\..\"
    if ($editTests) {
        $inpath = $inpath + "tests\"
        if ($subpath -ne ".")
        {
            $inpath = $inpath + "pythonpath\lingttest\"
        }
    } else {
        $inpath = $inpath + "pythonpath\lingt\"
    }
    $inpath = $inpath + $subpath
    #echo "EDITOR = $EDITOR"
    #echo "inpath = '$inpath'"
    if ($subpath -eq ".")
    {
        & $EDITOR $inpath\*.py
    } else {
        & $EDITOR (gci $inpath\*.py -recurse | where {
            $_.name -notmatch '__init__.py'})
    }
}
if ($tests.IsPresent) {
    #$SUBPATHS = @(".", "ui", "app", "access", "topdown", "utils")
    $SUBPATHS = @(".", "*")
} else {
    $SUBPATHS = @("ui", "app", "access", "utils")
}
Foreach ($subpath in $SUBPATHS) {
    $ps = [PowerShell]::Create()
    $ps.AddScript($block)
    $ps.AddArgument($PSScriptRoot)
    $ps.AddArgument($subpath)
    $ps.AddArgument($tests.IsPresent)
    $myjob = $ps.BeginInvoke()
    While (-Not $myjob.IsCompleted) {}
    $ps.EndInvoke($myjob)
    $ps.Dispose()
    sleep 0.75
}
