rem @echo off
:: Adapted by Jim Kornelsen 5-Dec-2012.
:: Based on jan@biochemfusion.com 2009.

SET IDL_FILE=..\idl\XCalcFunctions
SET OOO_HOME=C:\Program Files\LibreOffice 3.6
set SDK_HOME=C:\Program Files\OpenOffice.org 3 SDK\sdk

SET OOO_BIN_DIR=%OOO_HOME%\program
SET TOOLS_BIN_DIR=%SDK_HOME%\bin

:: The IDL tools rely on supporting files in the main OOo installation.
PATH=%PATH%;%OOO_HOME%\URE\bin

SET IDL_INCLUDE_DIR=%SDK_HOME%\idl

"%TOOLS_BIN_DIR%\idlc.exe" -w -I "%IDL_INCLUDE_DIR%" %IDL_FILE%.idl

:: Convert compiled IDL to loadable type library file.
:: First remove existing .rdb file, otherwise regmerge will just
:: append the compiled IDL to the resulting .rdb file. The joy of
:: having an .rdb file with several conflicting versions of compiled
:: IDL is very very limited - don't go there.
if exist %IDL_FILE%.rdb. (
del %IDL_FILE%.rdb
)
"%OOO_HOME%\URE\bin\regmerge.exe" %IDL_FILE%.rdb /UCR %IDL_FILE%.urd

del %IDL_FILE%.urd

