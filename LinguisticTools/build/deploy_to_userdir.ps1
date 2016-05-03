# vim: set filetype=conf :
#------------------------------------------------------------------------------
#
# Created by Jim Kornelsen on 16-Sep-2015.
#
# 24-Sep-15 JDK  Allow execution from a different location.
# 04-Nov-15 JDK  Do not pause if run from command line.
# 03-May-16 JDK  Copy to pythonpath instead of assimilating.
#
# Copy code the LO/AOO user directory, so it can be run from Tools -> Macros.
#
# The file componentsWrapper.py uses all of the lingt package.
# Likewise runTestSuite.py uses all of lingttest.
#
#------------------------------------------------------------------------------
#$OFFICEAPP = "OpenOffice\4"
$OFFICEAPP = "LibreOffice\4"
$DEPLOYDIR = "$env:APPDATA\$OFFICEAPP\user\Scripts\python"
$DEPLOY_PYTHONPATH = "$DEPLOYDIR\pythonpath"
$SRCDIR = "$PSScriptRoot\.."
$TESTDIR = "$SRCDIR\tests"

Foreach ($dir in @("$DEPLOY_PYTHONPATH\lingt",
                   "$DEPLOY_PYTHONPATH\lingttest",
                   "$DEPLOY_PYTHONPATH\grantjenks")) {
    if(Test-Path -PathType Container -Path $dir) {
        echo "Removing $dir"
        Remove-Item -Recurse -Force $dir
    }
}
if(!(Test-Path -PathType Container -Path $DEPLOY_PYTHONPATH)) {
    New-Item -ItemType directory -Path $DEPLOY_PYTHONPATH
}
Copy-Item -recurse "$SRCDIR\pythonpath\*" $DEPLOY_PYTHONPATH
Copy-Item -recurse "$TESTDIR\pythonpath\*" $DEPLOY_PYTHONPATH
Copy-Item -recurse "$TESTDIR\runTestSuite.py" $DEPLOYDIR
Copy-Item -recurse "$TESTDIR\componentsWrapper.py" $DEPLOYDIR

echo "Copied to $DEPLOYDIR"
if ((Get-ExecutionPolicy -Scope Process) -eq 'Bypass')
{
    # This script was probably invoked via "Run with Powershell" rather
    # than from a command line.
    pause
}

