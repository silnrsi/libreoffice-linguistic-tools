# vim: set filetype=conf :
#------------------------------------------------------------------------------
#
# Created by Jim Kornelsen on 16-Sep-2015.
#
# 24-Sep-15 JDK  Allow execution from a different location.
# 04-Nov-15 JDK  Do not pause if run from command line.
#
# Assimilate and copy componentsWrapper.py,
# which incorporates all of the lingt package.
# Likewise runTestSuite.py incorporates all of lingttest.
#
#------------------------------------------------------------------------------
# Assimilate component code into single large files.
& python.exe "$PSScriptRoot\assimilate.py" tests quiet

#$OFFICEAPP = "OpenOffice\4"
$OFFICEAPP = "LibreOffice\4"
$DEPLOYDIR = "$env:APPDATA\$OFFICEAPP\user\Scripts\python\"

# Copy code to where it can be run in Office from Tools -> Macros.
if(!(Test-Path -PathType Container -Path $DEPLOYDIR)) {
    New-Item -ItemType directory -Path $DEPLOYDIR
}
copy "$PSScriptRoot\assimilated_code\*.py" $DEPLOYDIR

echo "Copied to $DEPLOYDIR"
if ((Get-ExecutionPolicy -Scope Process) -eq 'Bypass')
{
    # This script was probably invoked via "Run with Powershell" rather
    # than from a command line.
    pause
}

