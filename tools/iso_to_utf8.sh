#!/usr/bin/env bash

for f in /home/team43/Projects/en-tw/content/other/*.md
do
  encoding=`file -i $f | cut -f 2 -d";" | cut -f 2 -d=`
  case $encoding in
    iso-8859-1)
    echo $f, $encoding
    iconv -f iso-8859-1 -t utf-8 $f > $f.utf8
    mv $f.utf8 $f
    ;;
    us-ascii)
    echo $f, $encoding
    ;;
  esac
done
