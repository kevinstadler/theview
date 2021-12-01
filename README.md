## the view

scripts for recovering views. see also: [topographic recovery – quantitative](https://thiswasyouridea.com/theview/#strategy-3-topographic-recovery-quantitative)

### `prominence.py`

implementation of [computing topographic prominence from contour line vector data](https://kevinstadler.github.io/notes/computing-topographic-prominence-from-contour-line-vector-data/).

```
# dependencies
pip3 install geopandas rtree
```

```
usage: prominence.py [-h] [-o OUT] file

generate contour polygons with prominence information from elevation-labelled contour lines

positional arguments:
  file               input file of elevation-labelled contour linestrings (any format supported by geopandas)

optional arguments:
  -h, --help         show this help message and exit
  -o OUT, --out OUT  output filename
```

### `stitch-lines.py`

dissolves lines split across several input files back together (within tolerance) based on some grouping attribute. useful for stitching together contour line data from separate tiles. (wasted two hours with Shapely's `unary_union`/`mergelines` which were not producing reliable results, before giving up and doing a low-level implementation in less than half the time)

```
# dependencies
pip3 install fiona
```

```
usage: stitch-lines.py [-h] [--groupby GROUPBY] [--attributename ATTRIBUTENAME] [-t TOLERANCE] [-o OUT] files [files ...]

dissolves lines split across several input files back together (within tolerance) based on some grouping attribute

positional arguments:
  files                 input files (any format supported by fiona)

optional arguments:
  -h, --help            show this help message and exit
  --groupby GROUPBY     name of the grouping attribute in the input files
  --attributename ATTRIBUTENAME
                        name of the grouping attribute on the output file
  -t TOLERANCE, --tolerance TOLERANCE
                        dissolve end points that are up to this far from each other (in projection units)
  -o OUT, --out OUT     output filename
```

