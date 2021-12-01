#!/usr/local/bin/python3
import sys
from functools import reduce
from collections import OrderedDict

import fiona
#from shapely.geometry import shape
#from shapely.ops import linemerge, polygonize, snap, unary_union

import argparse
argparser = argparse.ArgumentParser(description='dissolves lines split across several input files back together (within tolerance) based on some grouping attribute')
argparser.add_argument('--groupby', default='elevation', help='name of the grouping attribute in the input files')
argparser.add_argument('--attributename', default='elevation', help='name of the grouping attribute on the output file')
argparser.add_argument('-t', '--tolerance', type=float, default=0, help='dissolve end points that are up to this far from each other (in projection units)')
argparser.add_argument('-o', '--out', default='out.shp', help='output filename')
argparser.add_argument('files', nargs='+', help='input files (any format supported by fiona)')

args = argparser.parse_args()

def ends(pt):
  return (pt['geometry']['coordinates'][0], pt['geometry']['coordinates'][-1])

def isring(el):
  e = ends(el)
  return e[0] == e[1]

def closeenough(a, b):
  return abs(a[0] - b[0]) < args.tolerance and abs(a[1] - b[1]) < args.tolerance

# return the first pair of (0,0)
def canconnect(a, b):
  a = ends(a)
  b = ends(b)
  for i in range(2):
    for j in range(2):
      if closeenough(a[i], b[j]):
        return (i, j)
  return ()

# a always stays complete, b might be feshuffled
def connectcoords(a, b, pos):
  a = a['geometry']['coordinates']
  b = b['geometry']['coordinates']
  if not closeenough(a[0] if pos[0] == 0 else a[-1], b[0] if pos[1] == 0 else b[-1]):
    raise ValueError
  p1 = [ el for el in (reversed(a) if pos[0] == 0 else a) ]
  p2 = [ el for el in (b if pos[1] == 0 else reversed(b)) ]
  if not closeenough(p1[-1], p2[0]):
    raise ValueError
  return p1 + p2[1:]

closed = []
unclosed = dict()
origcrs = None
for file in args.files:
  with fiona.open(file) as tile:
    origcrs = tile.crs
    print(f"{file}: {len(tile)} features")
    for el in tile:
      alt = el['properties'][args.groupby]
      #if alt % 2 != 0:
      #  continue
      if isring(el):
        closed.append(el)
        print('.', end="")
        continue
      if not alt in unclosed:
        unclosed[alt] = []
      candidates = unclosed[alt]
      linked = 0
      while True:
        con = ()
        for candidate in candidates:
          # see if/what connection can be made
          con = canconnect(el, candidate)
          if con:
            linked = linked + 1
            print(linked, end="")

            # merge
            candidates.remove(candidate)
            el['geometry']['coordinates'] = connectcoords(el, candidate, con)

            newends = ends(el)
            if closeenough(newends[0], newends[1]):
              # made a trivial ring!
              el['geometry']['coordinates'][-1] = el['geometry']['coordinates'][0] # connectcoords(candidate, el, can)
              if not isring(el):
                raise ValueError
            # exit loop on first match
            break

        if isring(el):
          print('O', end="")
          closed.append(el)
          break
        elif not con:
          print(',', end="")
          candidates.append(el)
          break

  #  print(f" (+?:{len(newunclosed)})")
  print(f"\nstate {len(closed)}:{reduce(lambda a, b: a+len(b), unclosed.values(), 0)}")

#poligoniter = polygonize()

schema = {'properties': OrderedDict([(args.attributename, 'float:9.2')]), 'geometry': '3D LineString'}
with fiona.open(args.out, mode='w', driver='ESRI Shapefile', schema = schema, crs = origcrs) as out:
  for cls in closed + [line for lines in unclosed.values() for line in lines]:
    if len(cls['geometry']['coordinates']) <= 2:
      print("skipping linestring that only has two points...")
      continue
    cls['properties'] = OrderedDict([(args.attributename, cls['properties'][args.groupby])])
    out.write(cls)

