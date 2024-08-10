#------------------------------------------------------------------------------
# Opens all python code for editing using a text editor, with each package in
# a separate window.
# Useful when run with a windows shortcut.
#
# Specify -tests to edit tests instead of the main code.
#------------------------------------------------------------------------------
param ([switch]$tests)

$block = {
    Param($psscriptroot, $subpath, [bool]$editTests)
    $EDITOR = "${Env:ProgramFiles}\Vim\vim91\gvim.exe"
    $inpath = "$psscriptroot\..\"
    if ($editTests) {
        $inpath = $inpath + "tests\"
        if ($subpath -ne ".") {
            $inpath = $inpath + "pythonpath\lingttest\"
        }
    } else {
        $inpath = $inpath + "pythonpath\lingt\"
    }
    $inpath = $inpath + $subpath
    if ($subpath -eq ".") {
        Start-Process $EDITOR "$inpath\*.py"
    } else {
        Start-Process $EDITOR (gci $inpath\*.py -recurse | where {
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
    Start-Sleep -Milliseconds 250
}
