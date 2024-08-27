#------------------------------------------------------------------------------
# Copy code to LO user directory, so it can be run from Tools > Macros.
#
# The file ComponentsWrapper.py uses all of the lingt package.
# Likewise runTestSuite.py uses all of lingttest.
#
# Before running on a new user directory,
# go into Tools > Macros > Organize Dialogs,
# and create a library called LingToolsBasic.
# Close LibreOffice, which will modify basic/dialog.xlc.
#------------------------------------------------------------------------------
$OFFICEAPP = "LibreOffice\4"
$DEPLOYDIR = "$env:APPDATA\$OFFICEAPP\user"
$DEPLOY_PY = "$DEPLOYDIR\Scripts\python"
$DEPLOY_PYTHONPATH = "$DEPLOY_PY\pythonpath"
$SRCDIR = "$PSScriptRoot\.."
$TESTDIR = "$SRCDIR\tests"

# Update timestamp so file will get reloaded.
$file = Get-Item "$TESTDIR\ComponentsWrapper.py"
$file.LastWriteTime = (Get-Date)

Foreach ($dir in @("$DEPLOY_PYTHONPATH\lingt",
                   "$DEPLOY_PYTHONPATH\lingttest",
                   "$DEPLOY_PYTHONPATH\grantjenks",
                   "$DEPLOY_PYTHONPATH\oxttools")) {
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
Copy-Item -recurse "$TESTDIR\runTestSuite.py" $DEPLOY_PY
Copy-Item -recurse "$TESTDIR\ComponentsWrapper.py" $DEPLOY_PY

$DEPLOY_BASIC = "$DEPLOYDIR\basic\LingToolsBasic"
Copy-Item -recurse "$SRCDIR\LingToolsBasic\*" $DEPLOY_BASIC

echo "Copied to $DEPLOYDIR"
if ((Get-ExecutionPolicy -Scope Process) -eq 'Bypass')
{
    # This script was probably invoked via "Run with Powershell" rather
    # than from a command line.
    pause
}
