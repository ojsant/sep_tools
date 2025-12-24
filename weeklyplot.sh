#!/bin/bash

# Usage instructions (14.11.2025): call signature is "bash weeklyplot.sh <spacecraft> <year> <week>",
# where spacecraft is either "l1", "sta", "psp" or "solo", year is the year you want plots for and week is the week
# number counted up from the first day of the first week of the year (might be in December!). So if the whole thing
# crashes midway (which it will 100% at some point), then you can continue from where it crashed by looking at
# the printed week number.
# 
# The reason for the bash script workaround I believe was that the memory would get a bit clogged up using one
# Python interpreter. So for every week just throw the interpreter out and start a new one

for i in $(seq $3 53)
do
    echo Week $i
    python3 weekly_plot.py $1 $2 $i
done


