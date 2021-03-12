#!/bin/bash

pyfiles=$(find $1 -name "*.py")

if [ ! -d "typeinfer_results" ];
then
    mkdir ./typeinfer_results
fi

for file in $pyfiles
do
java -jar $2 $file ./typeinfer_results
echo "---------------------------------Scan File: $file--------------------------------------"
python3.8 featureScanner.py -s $file -t ./typeinfer_results/${file##*/}.html -c csv_res.csv 
done