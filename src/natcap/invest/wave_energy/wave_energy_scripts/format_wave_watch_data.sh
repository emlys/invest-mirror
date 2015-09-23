#!/bin/bash
# NAME
# This script is designed to be used on a wave watch 3 text file. The script
# will remove unnecessary commas that are often found at line endings, as well
# as the headers for the Wave Period and Wave Height rows and columns. 
#
# The format of the file being input should have the first two lines set as the
# ranges of the wave period and wave height where each line starts with the
# column headers as "TPbin=" and "HSbin=". The following lines should start with
# and I,J position for each set of wave watch data, followed by the data where
# each line is a row and each entry in the row is the row-column that matches
# the "TPbin" and "HSbin" positions. An example is provided below:
#
#TPbin=.37500E+00,.100000E+01,.150000E+01,.200000E+01,.250000E+01,.300000E+01,.350000E+01,.400000E+01,.450000E+01,.500000E+01,.550000E+01,.600000E+01,.650000E+01,.700000E+01,.750000E+01,.800000E+01,.850000E+01,.900000E+01,.950000E+01,.100000E+02,.105000E+02,.110000E+02,.115000E+02,.120000E+02,.125000E+02,.130000E+02,.135000E+02,.140000E+02,.145000E+02,.150000E+02,.155000E+02,.160000E+02,.165000E+02,.170000E+02,.175000E+02,.180000E+02,.185000E+02,.190000E+02,.195000E+02,.200000E+02,
#HSbin=.37500E+00,.100000E+01,.150000E+01,.200000E+01,.250000E+01,.300000E+01,.350000E+01,.400000E+01,.450000E+01,.500000E+01,.550000E+01,.600000E+01,.650000E+01,.700000E+01,.750000E+01,.800000E+01,.850000E+01,.900000E+01,.950000E+01,.100000E+02,.105000E+02,.110000E+02,.115000E+02,.120000E+02,.125000E+02,.130000E+02,.135000E+02,.140000E+02,.145000E+02,.150000E+02,.155000E+02,.160000E+02,.165000E+02,.170000E+02,.175000E+02,.180000E+02,.185000E+02,.190000E+02,.195000E+02,.200000E+02,
#I,102,J,370
#.00000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,
#.00000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.300000E+01,.300000E+01,.900000E+01,.300000E+01,.300000E+02,.360000E+02,.210000E+02,.120000E+02,.300000E+02,.120000E+02,.210000E+02,.120000E+02,.180000E+02,.000000E+00,.000000E+00,.000000E+00,.600000E+01,.600000E+01,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,
#.00000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.600000E+01,.180000E+02,.000000E+00,.300000E+01,.900000E+01,.300000E+01,.900000E+01,.210000E+02,.570000E+02,.570000E+02,.870000E+02,.180000E+03,.267000E+03,.228000E+03,.291000E+03,.129000E+03,.234000E+03,.105000E+03,.156000E+03,.720000E+02,.108000E+03,.270000E+02,.300000E+02,.300000E+01,.120000E+02,.150000E+02,.900000E+01,.210000E+02,.600000E+01,.900000E+01,
# .......
#I,102,J,371
#.00000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,
#.00000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.600000E+01,.300000E+01,.900000E+01,.300000E+01,.270000E+02,.390000E+02,.210000E+02,.900000E+01,.330000E+02,.120000E+02,.240000E+02,.900000E+01,.180000E+02,.000000E+00,.000000E+00,.000000E+00,.600000E+01,.300000E+01,.300000E+01,.000000E+00,.000000E+00,.000000E+00,.000000E+00,.000000E+00,
# ..............

# EXAMPLE RUN: ./format_wave_watch_data.sh < wave_watch_data.txt

# 'sed' is a find and replace command. First we look for commas that come
# at the end of the line and delete. Then find and delete the column headers
# "TPbin=" and "HSbin="
sed 's/,[^,0-9]*$//g' | sed 's/^TPbin=//' | sed 's/^HSbin=//'