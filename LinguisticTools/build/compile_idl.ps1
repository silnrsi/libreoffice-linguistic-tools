# Created by Jim Kornelsen on August 22, 2023.

$idlFile = "../idl/XCalcFunctions"
$loHome = "C:/Program Files/LibreOffice/program"
$sdkHome = "C:/libreoffice7.5.3.2/sdk"

$tools = "$sdkHome/bin"
$unoTypes = "$loHome/types.rdb"
$offTypes = "$loHome/types/offapi.rdb"

& "$tools/unoidl-write.exe" $unoTypes $offTypes "$idlFile.idl" "$idlFile.rdb"
