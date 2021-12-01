#!/usr/local/bin/python3
import numpy as np
import pandas as pd
pd.options.mode.chained_assignment = None
import geopandas as gpd

# pygeos sjoin gives widely inaccurate results, so force using rtree instead
#import pygeos
gpd.options.use_pygeos = False

from geopandas import GeoSeries
from geopandas.tools import sjoin
from shapely.geometry import Polygon

import argparse
argparser = argparse.ArgumentParser(description='generate contour polygons with prominence information from elevation-labelled contour lines')
argparser.add_argument('-o', '--out', default='prominence.shp', help='output filename')
argparser.add_argument('file', help='input file of elevation-labelled contour linestrings (any format supported by geopandas)')
#argparser.add_argument('--attribute', default='elevation', help='name of the elevation attribute')
args = argparser.parse_args()

ct = gpd.read_file(args.file)
ct['poly'] = GeoSeries([Polygon(g) for g in ct.geometry])
ct['area'] = ct.poly.area

# sorting by area as secondary is important for two reasons:
# 1. assume larger areas of the same elevation are actually a little higher, so are assigned prominence first
# 2. when selecting basin containers we want to stick to the smallest containing one,
# (so we aggregate using .max(), maybe .last() also ok)
ct.sort_values(['elevation', 'area'], ascending=[False, False], inplace=True, na_position='first')
ct.reset_index(drop=True, inplace=True)
ct.reset_index(inplace=True)

# now that contour lines have been re-sorted, make dedicated polygon dataframe for spatial joins
polys = gpd.GeoDataFrame(geometry=ct.poly)
# FIXME get proj from input file
polys = polys.set_crs(epsg=31297, inplace=True)
# and put in an appropriate projection
print("Reprojecting...")
#polys.to_crs('ESRI:102030', inplace=True)
polys.to_crs('EPSG:31297', inplace=True)

centroids = gpd.GeoDataFrame(geometry=polys.geometry.centroid)

els = list(ct.elevation.unique())
interval = els[0] - els[1]

# index of the 'parent' (containing) contour line
ct['parent'] = np.repeat(-1, len(ct))

for ele in els:
  left = sum(ct.elevation == ele)
  descentparents = sjoin(centroids[ct.elevation == ele], polys[ct.elevation == ele - interval], predicate='within', how='left') # or within or intersects
  # if there's no direct descent parent, maybe it is a basin within a
  # (usually much wider) contour line of the same elevation
  orphans = descentparents[np.isnan(descentparents.index_right)].index
  basins = 0
  if len(orphans):
    # TODO only keep polygons larger than the smallest orphan as candidates
#    largestorphan = max(ct.area)
    basinparents = sjoin(centroids.loc[orphans], polys[ct.elevation == ele], predicate='within', how='left')
    # FIXME drop multiple matches! also group by but select largest (=first/min)
    basinparents.dropna(inplace = True)
    basins = sum(basinparents.index != basinparents.index_right)
  
  # if there's multiple, only keep smallest (because that will be the direct parent)
  descentparents.dropna(inplace=True)
  groups = descentparents[['index_right']].groupby(descentparents.index, sort=False)
  # because we originally sorted like this, we know it's the highest index! yesss!
  descentparents = groups.max()

  # using pygeos' sjoin I found that I got many incorrect results, basd on this check:
  # p.geometry.within(polys.geometry[p.index_right])]
#  invalid = [i for i, p in descentparents.iterrows() if np.isnan(p.index_right)]
#  print(invalid)
#  descentparents.drop(invalid, inplace=True)
  
  # actual matches found
  print(ele)
  print(left)
  print(len(descentparents) + basins)
  ct.parent[descentparents.index] = descentparents.index_right
  # now that known parents have been assigned, we can use this information to correctly
  # assign the lower parent of basins
  if basins:
    print("found basin(s)")
    # FIXME there might be recursive basin-parenting happening here which would require a loop
    ct.parent[basinparents.index] = ct.parent[basinparents.index_right]
#    print(ct.parent[basinparents.index])
  print()

ct['prominence'] = np.repeat(None, len(ct))
for i in range(len(ct)):
  if ct.prominence[i] != None or ct.parent[i] == -1:
    continue
#  print(i)
  parent = ct.parent[i]
  print(f'{i} @ {ct.elevation[i]}: ', end = '')
  while ct.prominence[parent] == None:
    print('.', end = '')
    ct.prominence[parent] = 0
    if ct.parent[parent] == -1 or np.isnan(ct.parent[parent]):
      break
    parent = ct.parent[parent]
  # ok, compute prominence
  ct.prominence[i] = ct.elevation[i] - ct.elevation[parent]
  print(f'{parent} @ {ct.elevation[parent]}')

peaks = [i for i, p in enumerate(ct.prominence > 0) if p]
peaks = gpd.GeoDataFrame({ 'elevation': ct.elevation[peaks], 'prominence': pd.to_numeric(ct.prominence[peaks]), 'geometry': polys.geometry[peaks] }, crs='ESRI:102030')

# TODO filter only positive prominence
peaks.to_file(args.out)
