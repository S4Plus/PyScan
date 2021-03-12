#!/bin/bash

pyfiles=$(find $1 -name "*.py")

if [ ! -d "standard_libs" ];
then
    mkdir ./standard_libs
fi

for file in $pyfiles
do
path=${file#*Lib/}
filename=${path%*.py}
if [[ $path == */* ]]
then
    if [ ! -d "standard_libs/${path%*/*.py}" ]
    then
        mkdir -p ./standard_libs/${path%*/*.py}
    fi
fi
python3.8 functionScanner.py -s $file -c ./standard_libs/$filename.csv
done