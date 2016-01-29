!/bin/sh
################################################################################
#
# unzip_tree.sh
#
# Created by Jim Kornelsen on July 5 2013
#
# Recursively go through each directory and unzip all .oxt files to a
# folder of the same name.
#
################################################################################

# handle spaces in filenames for bash
SAVEIFS=$IFS
IFS=$(echo -en "\n\b")

outnum=1
find $src -name "*.oxt" | sort | while read infile
do
    outdir=$outnum.$(basename "$infile" .oxt)
    #echo $outdir
    mkdir "$outdir" && unzip "$infile" -d "$outdir"
    outnum=$((outnum+1))
done

IFS=$SAVEIFS
