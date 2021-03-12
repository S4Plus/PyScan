#!/bin/bash

pyfiles=$(cat $1 | grep .py)

if [ ! -d "polymorphism_files" ];
then
    mkdir ./polymorphism_files
fi

for file in $pyfiles
do
path=${file#*Lib/}
filename=${path%.*}
if [[ $path == */* ]]
then
    if [ ! -d "polymorphism_files/${path%/*}" ]
    then
        mkdir -p ./polymorphism_files/${path%/*}
    fi
fi
python3.8 functionScanner.py -s ${file:0:${#file} - 1} -c ./polymorphism_files/$filename.csv -t ./typeinfer_results/${filename##*/}.py.html -p
done