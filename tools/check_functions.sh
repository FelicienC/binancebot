#!/usr/bin/env bash

for d in ../iac/functions/build/*/ ; do
    function_name=$(basename $d);
    pylint --output-format=colorized "${d}main.py"; 
done
