# vim: set filetype=conf :
#------------------------------------------------------------------------------
#
# Created by Jim Kornelsen on August 27, 2015.
#
# 30-Sep-15 JDK  Returns to original folder when finished.
# 04-Nov-15 JDK  Do not pause if run from command line.
#
# Removes unnecessary files.
# It is a good idea to run this before packing the add-on in order to reduce
# file size.
#
#------------------------------------------------------------------------------
chdir $PSScriptRoot
Remove-Item "assimilated_code/*"
Remove-Item "generating_code/*.csv"

# Go to LinguisticTools folder.
$OriginalFolder = Convert-Path(".")
chdir $PSScriptRoot\..

Get-ChildItem "*.pyc" -Recurse | Remove-Item
Get-ChildItem "*.swp" -Recurse | Remove-Item
Get-ChildItem "pylint.txt" -Recurse | Remove-Item
#Remove-Item "*.swp" -Recurse
#Remove-Item "pylint.txt" -Recurse
Get-ChildItem -Recurse | ?{ $_.PSIsContainer -And
                           ($_.Name -eq "__pycache__")} | Remove-Item -Recurse

#chdir $OriginalFolder

if ((Get-ExecutionPolicy -Scope Process) -eq 'Bypass')
{
    # This script was probably invoked via "Run with Powershell" rather
    # than from a command line.
    pause
}
