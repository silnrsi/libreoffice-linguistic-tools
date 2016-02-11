#!/bin/sh
# Created by Jim Kornelsen on March 11 2013
#
# 05-Apr-13 JDK  Remove assimilated code and CSV files.

find .. -warn -name \*.pyc -type f -delete
#find .. -warn -name \*.swp -type f -delete

rm -v "assimilated_code/"*
rm -v "generating_code/"*.csv

