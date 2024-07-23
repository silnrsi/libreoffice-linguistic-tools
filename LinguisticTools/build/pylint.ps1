#
# Sets paths to lingt and lingttest.
# Install if not yet done: pip3 install pylint
# To generate .pylintrc: pylint --generate-rcfile | out-file -encoding utf8 .pylintrc
#
# Then run for example: pylint --output-format=colorized lingt.access
#
$scriptDir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$fakes = Join-Path -Path $scriptDir -ChildPath "pylint-fakes"
$addOn = Join-Path -Path $scriptDir -ChildPath ".."
$workingDir = Join-Path -Path $addOn -ChildPath "pythonpath"
$pythonBase = "$env:ProgramFiles\Python312"
$pythonPath = "$addOn\pythonpath;$addOn\tests\pythonpath;$pythonBase;$fakes"
$pylintrc = "$scriptDir\pylintrc"

# Set environment variables for this session
$env:PYTHONPATH = $pythonPath
$env:PYLINTRC = $pylintrc

# Open a new PowerShell window at C:\abc
#Start-Process powershell -ArgumentList "-NoExit", "-WorkingDirectory $workingDir"
Start-Process powershell -ArgumentList "-NoExit", "-Command `"cd $workingDir;`""

