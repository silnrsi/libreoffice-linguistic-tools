@echo off
:: Windows make-file for DoobieDoo OOo Calc Add-in example.
:: Created by jan@biochemfusion.com, April 2009
:: Updated July 2009 - now using OOo 3.1.

SET OOO_HOME=C:\Program Files\OpenOffice.org 3

SET OOO_BIN_DIR=%OOO_HOME%\program
SET TOOLS_BIN_DIR=%OOO_HOME%\Basis\sdk\bin

SET PACKAGE_NAME=DoobieDoo

:: The IDL tools rely on supporting files in the main OOo installation.
PATH=%PATH%;%OOO_HOME%\URE\bin


::
:: Compile IDL file.
::

SET IDL_INCLUDE_DIR=%OOO_HOME%\Basis\sdk\idl
SET IDL_FILE=idl\X%PACKAGE_NAME%

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


::
:: Generate XML files.
::

"%OOO_BIN_DIR%\python.exe" src\generate_xml.py

::
:: Create .OXT file.
::

move manifest.xml %PACKAGE_NAME%\META-INF\
move description.xml %PACKAGE_NAME%\
move CalcAddIn.xcu %PACKAGE_NAME%\

move %IDL_FILE%.rdb %PACKAGE_NAME%\
copy src\doobiedoo.py %PACKAGE_NAME%\

del %PACKAGE_NAME%.oxt
cd %PACKAGE_NAME%\
"C:\program files\7-zip\7z.exe" a -r -tzip ..\%PACKAGE_NAME%.oxt *.*
cd ..

