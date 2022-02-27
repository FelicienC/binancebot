#!/usr/bin/env bash

coinlist="[";
cat coin.lst | ( while IFS=';' read coin_name; do
    echo "$coin_name"
    coinlist+="\"$coin_name\", "
    coin_name=`perl -e "print lc('$coin_name');"`

    for file_path in ../iac/views/*.yaml;
    do
        file_template=$(echo $file_path | sed "s/.*\///");
        file_destination=$(echo $file_template | sed "s/%coin%/$coin_name/");
        sed "s/%coin%/$coin_name/" $file_path > ../iac/views/build/$file_destination;
    done;
    for file_path in ../iac/schedueled_queries/*.yaml;
    do
        file_template=$(echo $file_path | sed "s/.*\///");
        file_destination=$(echo $file_template | sed "s/%coin%/$coin_name/");
        sed "s/%coin%/$coin_name/" $file_path > ../iac/schedueled_queries/build/$file_destination;
    done;
    for file_path in ../iac/procedures/*.yaml;
    do
        file_template=$(echo $file_path | sed "s/.*\///");
        file_destination=$(echo $file_template | sed "s/%coin%/$coin_name/");
        sed "s/%coin%/$coin_name/" $file_path > ../iac/procedures/build/$file_destination;
    done;
    for file_path in ../iac/tables/*.json;
    do
        file_template=$(echo $file_path | sed "s/.*\///");
        file_destination=$(echo $file_template | sed "s/%coin%/$coin_name/");
        sed "s/%coin%/$coin_name/" $file_path > ../iac/tables/build/$file_destination;
    done;
done

coinlist="${coinlist%??}]";
for d in ../iac/functions/*/ ; do
    if [ $d != ../iac/functions/build/ ]; then
        function_name=$(basename $d);
        rm -r ../iac/functions/build/$function_name;
        mkdir ../iac/functions/build/$function_name;
        for file_path in $d*;
        do
            file_template=$(echo $file_path | sed "s/.*\///");
            cat $file_path \
             | sed "s/\[\"BTC\", \"ETH\", \"SOL\"\]/$coinlist/" \
             | sed "s/trading-dv/$TF_VAR_project/" > ../iac/functions/build/$function_name/$file_template;
        done;
    fi;

done

);
