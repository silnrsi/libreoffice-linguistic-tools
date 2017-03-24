# vim: set filetype=conf :
#------------------------------------------------------------------------------
#
# Created by Jim Kornelsen on 24-Sep-2015.
#
# 04-Nov-15 JDK  Do not pause if run from command line.
# 11-Mar-17 JDK  Do not deploy by default.
#
# Build .oxt file.  Specify -deploy to deploy it to Office.
#
#------------------------------------------------------------------------------
$Deploy = $False
if($args[0] -eq "-deploy")
{
    Write-Host "Deploying"
    $Deploy = $True
}

# Go to LinguisticTools folder.
$OriginalFolder = Convert-Path(".")
chdir $PSScriptRoot\..

# The .oxt file gets built simply by zipping up the files.
# We use 7-zip to do this.
$OxtFile = "LinguisticTools.oxt"
$ZipOptions = @(
    "a",
    "-tZip",
    "-xr!*.swp",
    "-xr!*.pyc",
    "-xr!*.stats",
    "-xr!pylint.txt",
    "-xr!build/assimilated_code/*.*"
    )
$ZipInput = @(
    "build",
    "help",
    "idl",
    "LingToolsBasic",
    "META-INF",
    "pkg-desc",
    "pythonpath",
    "tests",
    "*.xcu",
    "Components.py",
    "description.xml"
    )
& "$env:ProgramFiles\7-Zip\7z.exe" @ZipOptions $OxtFile @ZipInput

if($Deploy)
{
    #$OFFICEDIR = "${Env:ProgramFiles(x86)}\OpenOffice 4"
    $OFFICEDIR = "${Env:ProgramFiles(x86)}\LibreOffice 5"

    # The unopkg tool deploys extensions programmatically.
    # This does the same thing as adding in Office from Tools -> Extensions.
    Write-Host "Removing old package"
    & "$OFFICEDIR\program\unopkg" remove "name.JimK.LinguisticTools"
    Write-Host "Adding new package"
    & "$OFFICEDIR\program\unopkg" add $OxtFile

    Write-Host "Finished packing and deploying."
}
chdir $OriginalFolder
if ((Get-ExecutionPolicy -Scope Process) -eq 'Bypass')
{
    # This script was probably invoked via "Run with Powershell" rather
    # than from a command line.
    pause
}
