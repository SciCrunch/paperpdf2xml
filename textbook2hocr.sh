#!/bin/bash

#
# usage: $0 <textbook-pdf-dir> <hocr-output-dir>
# 
mkdir -p $2
for x in `ls $1/*.pdf`; do
    echo $x
    prefix=`basename $x .pdf`
    echo $prefix
    pdftotree $x > $2/${prefix}.html
done
