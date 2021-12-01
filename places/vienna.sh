#!/bin/sh

for ((x=1; x<=5; x++)); do
  for ((y=2; y<=9; y++)); do
    for ((j=1; j<=4; j++)); do
      FILE="${x}${y}_${j}_dgm_iso.zip"
      if [ ! -f $FILE ]; then
        wget "https://www.wien.gv.at/ma41datenviewer/downloads/geodaten/dgm_iso_shp/$FILE"
        unzip -d vienna/ $FILE
      fi
    done
  done
done

../stitch-lines.py --groupby H_WIEN -o vienna.shp vienna/*.shp
../prominence.py vienna.shp
