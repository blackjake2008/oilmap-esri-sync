#!/usr/bin/env python
'''
@author David Stuebe <dstuebe@asasscience.com>
@file distribution_of_max_uniform_oil_thickness.py
@date 03/11/13
@description Calculates the distribution of the thickest spillet from each simulation
'''
import numpy
import logging
from collections import OrderedDict
from pystoch.exceptions import PyStochOperatorError
import helper_functions 

from pystoch.datatypes import DT
from pystoch.map_reduce_ops.thickest_spillet_op import thickest_spillet_op
from pystoch.map_reduce_ops.distribution_reduce import distribution_reduce

from pystoch.config import get_config
from pystoch.keywords import *

logger = logging.getLogger('pystoch.products.distribution_of_thickest_spillet')

product_name = 'distribution_of_thickest_spillet'

def add_product(ops_list, reduce_list, cleaner_list, grid_data, product_metadata):

    product_type = product_metadata[PRODUCT_TYPE]
    
    config = get_config()
    # This method now uses a quadratic index space
    nbins = config[product_type].thickness.bins
    bin_coefficient = config[product_type].thickness.coefficient
        
    dims, bin_values = grid_data.make_bin_data('thickness_bins', nbins, bin_coefficient)

    
    metadata={
        'units':'counts',
        'long_name':'Cumulative distribution of maximum spillet thickness',
        'coordinates':'thickness_bins latitude longitude',
        }
    reduce_array = grid_data.allocate(product_name,DT.INT32, grid_data_dimension=dims, metadata=metadata, only_if_msr=True)
    
    
    # Calculate cell area:
    cell_area = grid_data._grid.cell_area
    

    # Make a temporary array that will be used in the operation
    map_array = grid_data.allocate(product_name,DT.SPRECISION, metadata=metadata, store=False)
    
    #advective_dispersion = config[product_type].products.distribution_of_thickest_spillet.get('advective_dispersion',numpy.nan)
    #spillet_dispersion = advective_dispersion * 0.2 # m^2/s
      
    cfg_opts = config.get(product_type,{}).get(GRIDDED_PRODUCTS,{}).get(product_name,{})
        
    min_time = None
    if cfg_opts.get('min_time'):
        # use a helper function to setup for min time to thickness...        
        min_time = helper_functions.setup_min_time_to_thickness(grid_data, 'thickest_spillet', reduce_list)
    
    if cfg_opts.get('run_stats'):
        # use a helper function to setup the run stats
        run_stats = helper_functions.setup_run_stats(
            grid_data, 
            'area_oiled_stats_by_thickest_spillet_method', 
            'Area oiled statistics for each run by thickness using the thickest spillet method',
            product_metadata, 
            map_array,
            cell_area,
            'm^2',
            reduce_list
            )
    
      
        
    coroutine = thickest_spillet_op(map_array)
    # calculates the maximum oil thickness in each grid cell during a simulation
    
    # Append the operation coroutine to the list
    ops_list.append(coroutine)
    
    #bins the distribution of max oil thickness from each simulation
    coroutine = distribution_reduce(reduce_array, bin_coefficient,  product_metadata[NSIMS])
    reduce_list.append((coroutine, map_array))
    
    # Now add a reset value for the map array
    cleaner_list.append((map_array,0))
    