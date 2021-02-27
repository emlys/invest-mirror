"""Stormwater Retention"""
import logging
import numpy
import pygeoprocessing
import taskgraph

from . import validation
from . import utils

LOGGER = logging.getLogger(__name__)


ARGS_SPEC = {
    "model_name": "Stormwater Retention",
    "module": __name__,
    "userguide_html": "stormwater.html",
    "args": {
        "workspace_dir": validation.WORKSPACE_SPEC,
        "results_suffix": validation.SUFFIX_SPEC,
        "n_workers": validation.N_WORKERS_SPEC,
        "lulc_path": {
            "type": "raster",
            "bands": {1: {"type": "code"}},
            "required": True,
            "about": (
                "A GDAL-supported raster representing land use/land cover "
                "of the area"),
            "name": "land use/land cover"
        },
        "soil_groups_path": {
            "type": "raster",
            "bands": {
                1: {
                    "type": "option_string",
                    "options": ["1", "2", "3", "4"]
                }
            },
            "required": True,
            "about": (
                "Raster map of hydrologic soil groups, where 1, 2, 3, and 4 "
                "correspond to groups A, B, C, and D respectively"),
            "name": "soil groups"
        },
        "precipitation_path": {
            "type": "raster",
            "bands": {1: {"type": "number", "units": "millimeters"}},
            "required": True,
            "about": ("Precipitation raster"),
            "name": "precipitation"
        },
        "biophysical_table": {
            "type": "csv",
            "columns": {
                "lucode": {"type": "code"},
                "EMC_P": {"type": "number", "units": "mg/L"},
                "EMC_N": {"type": "number", "units": "mg/L"},
                "RC_A": {"type": "ratio"},
                "RC_B": {"type": "ratio"},
                "RC_C": {"type": "ratio"},
                "RC_D": {"type": "ratio"},
                "IR_A": {"type": "ratio"},
                "IR_B": {"type": "ratio"},
                "IR_C": {"type": "ratio"},
                "IR_D": {"type": "ratio"}
            },
            "required": True,
            "about": "biophysical table",
            "name": "biophysical table"
        },
        "adjust_retention_ratios": {
            "type": "boolean",
            "required": True,
            "about": "Whether to adjust retention ratios using road centerlines",
            "name": "adjust retention ratios"
        },
        "retention_radius": {
            "type": "number",
            "units": "meters",
            "required": "adjust_retention_ratios",
            "about": "Radius around each pixel to adjust retention ratios",
            "name": "retention radius"
        },
        "road_centerlines_path": {
            "type": "vector",
            "fields": {},
            "required": "adjust_retention_ratios",
            "about": "Map of road centerlines",
            "name": "road centerlines"
        },
        "watersheds_path": {
            "type": "vector",
            "fields": {},
            "required": False,
            "about": "Aggregation areas",
            "name": "watersheds"
        },
        "replacement_cost": {
            "type": "number",
            "units": "currency",
            "required": False,
            "about": "Replacement cost of stormwater retention devices",
            "name": "replacement cost"
        }
    }
}


FILES = {
    'lulc_aligned_path': 'intermediate/lulc_aligned.tif',
    'soil_group_aligned_path': 'intermediate/soil_group_aligned.tif',
    'precipitation_aligned_path': 'intermediate/precipitation_aligned.tif',
    'retention_ratio_path': 'retention_ratio.tif',
    'retention_volume_path': 'retention_volume.tif',
    'infiltration_ratio_path': 'infiltration_ratio.tif',
    'infiltration_volume_path': 'infiltration_volume.tif'
}


def execute(args):

    align_inputs = [args['lulc_path'], args['soil_groups_path'], args['precipitation_path']]
    align_outputs = [
        FILES['lulc_aligned_path'],
        FILES['soil_group_aligned_path'], 
        FILES['precipitation_aligned_path']]

    task_graph = taskgraph.TaskGraph(args['workspace_dir'], args['n_workers'])



    # Align all three input rasters to the same projection
    align_task = task_graph.add_task(
        func=pygeoprocessing.align_and_resize_raster_stack,
        args=(
            align_inputs, align_outputs, interpolate_list,
            pixel_size, 'intersection'),
        kwargs={
            'base_vector_path_list': (args['aoi_path'],),
            'raster_align_index': align_index},
        target_path_list=output_align_list,
        task_name='align rasters')


    # Build a lookup dictionary mapping each LULC code to its row
    biophysical_dict = utils.build_lookup_from_csv(
        args['biophysical_table'], 'lucode')

    # Make ratio lookup dictionaries mapping each LULC code to
    # a ratio for each soil group
    retention_ratio_dict = {
        lucode: {
            'A': row['RC_A'],
            'B': row['RC_B'],
            'C': row['RC_C'],
            'D': row['RC_D'],
        } for lucode, row in biophysical_dict
    }
    infiltration_ratio_dict = {
        lucode: {
            'A': row['IR_A'],
            'B': row['IR_B'],
            'C': row['IR_C'],
            'D': row['IR_D'],
        } for lucode, row in biophysical_dict
    }


    # Calculate stormwater retention ratio and volume from
    # LULC, soil groups, biophysical table, and precipitation

    retention_ratio_task = task_graph.add_task(
        func=calculate_stormwater_ratio,
        args=(
            FILES['lulc_aligned_path'],
            FILES['soil_group_aligned_path'],
            retention_ratio_dict,
            FILES['retention_ratio_path']),
        target_path_list=[FILES['retention_ratio_path']],
        task_name='calculate stormwater retention ratio'
    )

    # (Optional) adjust stormwater retention ratio using roads
    if args['adjust_retention_ratios']:
        adjust_retention_ratio_task = task_graph.add_task(
            func=adjust_stormwater_retention_ratio,
            args=(
                FILES['retention_ratio_path'],
                args['road_centerlines_path'],
                FILES['adjusted_retention_ratio_path']),
            target_path_list=[FILES['adjusted_retention_ratio_path']],
            task_name='adjust stormwater retention ratio'
        )
        final_retention_ratio_path = FILES['adjusted_retention_ratio_path']
    else:
        final_retention_ratio_path = FILES['retention_ratio_path']

    retention_volume_task = task_graph.add_task(
        func=calculate_stormwater_volume,
        args=(
            final_retention_ratio_path,
            args['precipitation_path'],
            FILES['retention_volume_path']),
        target_path_list=[FILES['retention_volume_path']],
        task_name='calculate stormwater retention volume'
    )


    # (Optional) Calculate stormwater infiltration ratio and volume from
    # LULC, soil groups, biophysical table, and precipitation

    infiltration_ratio_task = task_graph.add_task(
        func=calculate_stormwater_ratio,
        args=(
            FILES['lulc_aligned_path'],
            FILES['soil_group_aligned_path'],
            infiltration_ratio_dict,
            FILES['infiltration_ratio_path']),
        target_path_list=[FILES['infiltration_ratio_path']],
        task_name='calculate stormwater infiltration ratio'
    )

    infiltration_volume_task = task_graph.add_task(
        func=calculate_stormwater_retention_volume,
        args=(
            FILES['infiltration_ratio_path']
            args['precipitation_path'],
            FILES['infiltration_volume_path']),
        target_path_list=[FILES['infiltration_volume_path']],
        task_name='calculate stormwater retention volume'
    )

    # Calculate avoided pollutant load from retention volume and biophysical table

    # get all EMC columns from an arbitrary row in the dictionary
    # strip the first four characters off 'EMC_pollutant' to get pollutant name
    emc_columns = [key for key in biophysical_table.keys()[0] 
        if key.startswith('EMC_')]
    pollutants = [key[4:] key in  emc_columns]

    for pollutant in pollutants:
        avoided_pollutant_load_path = f'avoided_pollutant_load_{pollutant}.tif'
        lulc_emc_lookup = {
            lucode: row[f'EMC_{pollutant}'] for lucode, row in biophysical_dict.entries()
        }

        avoided_pollutant_load_task = task_graph.add_task(
            func=calculate_avoided_pollutant_load,
            args=(
                FILES['retention_path'],
                lulc_emc_lookup,
                avoided_pollutant_load_path),
            target_path_list=[avoided_pollutant_load_path],
            task_name=f'calculate avoided pollutant {pollutant} load'
        )


    # (Optional) Valuation

    valuation_task = task_graph.add_task(
        func=calculate_retention_value,
        args=(
            FILES['retention_path'],
            args['replacement_cost'],
            FILES['retention_value_path']),
        target_path_list=[FILES['retention_value_path']],
        task_name='calculate stormwater retention value'
    )


    # (Optional) Aggregate to watersheds
    aggregation_task = task_graph.add_task(
        func=aggregate_values,
        args=(
            ))


def calculate_stormwater_ratio(lulc_path, soil_group_path, 
        ratio_lookup, output_path):
    """Make stormwater retention or infiltration ratio map from LULC and
       soil group data.

    Args:
        lulc_path (str): path to a LULC raster whose LULC codes exist in the
            biophysical table
        soil_group_path (str): path to a soil group raster with pixel values
            1, 2, 3, and 4 corresponding to hydrologic soil groups A, B, C, and D
        ratio_lookup (dict): a lookup dictionary of ratios for each pair of 
            LULC code and soil group. Each LULC code is mapped to a dictionary
            with keys 'A', 'B', 'C', and 'D', which map to the ratio for that
            LULC code x soil group pair.
        output_path: path to write out the retention ratio raster to

    Returns:
        None
    """
    ratio_nodata = -1

    def ratio_op(lulc_array, soil_group_array):

        # initialize an array of the output nodata value
        ratio_array = numpy.full(lulc_array.shape, ratio_nodata)

        for lucode in ratio_lookup:
            lucode_mask = (lulc_array == lucode)

            for soil_group in ['A', 'B', 'C', 'D']:
                soil_group_mask = (soil_group_array == soil_group)

                ratio_array[(lucode_mask & soil_group_mask)] = ratio_lookup[lucode][soil_group]

        return ratio_array


def calculate_stormwater_volume(ratio_path, precipitation_path, output_path):
    """Make stormwater retention or infiltration volume map from ratio and 
       precipitation.

    Args:
        ratio_path (str): path to a raster of stormwater ratios
        precipitation_path (str): path to a raster of precipitation amounts
        output_path (str): path to write out the volume results (raster)

    Returns:
        None
    """


    def volume_op(ratio_array, precipitation_array):

        volume_array = numpy.full(ratio_array.shape, volume_nodata)
        nodata_mask = (
            ratio_array != ratio_nodata & 
            precipitation_array != precipitation_nodata)

        # precipitation (mm/yr) * pixel area (m^2) * 
        # 0.001 (m/mm) * ratio = volume (m^3/yr)
        volume_array[nodata_mask] = (
            precipitation_array[nodata_mask] *
            ratio_array[nodata_mask] *
            pixel_area * 0.001)

        return volume_array


def calculate_avoided_pollutant_load(lulc_path, retention_volume_path, 
        lulc_emc_lookup, output_path):
    """Make avoided pollutant load map from retention volumes and LULC event 
       mean concentration data.

    Args:
        lulc_path (str): path to a LULC raster whose LULC codes exist in the
            EMC lookup dictionary
        retention_volume_path: (str) path to a raster of stormwater retention
            volumes in m^3
        lulc_emc_lookup (dict): a lookup dictionary where keys are LULC codes 
            and values are event mean concentration (EMC) values in mg/L for 
            the pollutant in that LULC area.
        output_path (str): path to write out the results (raster)

    Returns:
        None
    """

    def pollutant_load_op(lulc_array, retention_volume_array):

        load_array = numpy.full(lulc_array.shape, load_nodata)

        nodata_mask = (
            lulc_array != lulc_nodata &
            retention_volume_array != retention_volume_nodata)

        for lucode in lulc_emc_lookup:
            lucode_mask = (lulc_array == lucode)

            # EMC for pollutant (mg/L) * 1000 (L/m^3) * retention (m^3)
            # = pollutant load (mg)
            load_array[lucode_mask & nodata_mask] = (
                lulc_emc_lookup[lucode] * 1000 * 
                retention_volume_array[lucode_mask & nodata_mask])

        return load_array


def calculate_retention_value(retention_volume_path, replacement_cost, output_path):
    """Calculate retention value from retention volume and replacement cost.
    Args:
        retention_volume_path (str): path to retention volume raster (m^3/pixel)
        replacement_cost (float): value in currency units/m^3
        output_path (str): path to write out valuation results raster

    Returns:
        None
    """

    def retention_value_op(retention_volume_array):
        value_array = numpy.full(retention_volume_array.shape, value_nodata)
        nodata_mask = (retention_volume_array != retention_volume_nodata)

        # retention (m^3) * replacement cost ($/m^3) = retention value ($)
        value_array[nodata_mask] = retention_volume_array[nodata_mask] * replacement_cost


def aggregate_results(aoi_path, retention_ratio, retention_volume, 
        infiltration_ratio, infiltration_volume, avoided_pollutant_loads, 
        retention_value, output_path):
    """Aggregate outputs into regions of interest.

    Args:
        aoi_path (str): path to vector of polygon(s) to aggregate over
        retention_ratio (str): path to stormwater retention ratio raster
        retention_volume (str): path to stormwater retention volume raster
        infiltration_ratio (str): path to stormwater infiltration ratio raster
        infiltration_volume (str): path to stormwater infiltration volume raster
        avoided_pollutant_loads (list[str]): list of paths to avoided pollutant
            load rasters
        retention_value (str): path to retention value raster
        output_path (str): path to write out aggregated vector data

    Returns:
        None
    """

    # Copy the AOI polygons into the output vector
    aoi_vector = gdal.OpenEx(aoi_path, gdal.OF_VECTOR)
    driver = gdal.GetDriverByName('ESRI Shapefile')
    driver.CreateCopy(output_path, aoi_vector)
    gdal.Dataset.__swig_destroy__(original_aoi_vector)
    original_aoi_vector = None

    aggregate_vector = gdal.OpenEx(output_path, 1)
    aggregate_layer = aggregate_vector.GetLayer()

    aggregations = [
        (retention_ratio, 'RR_mean', 'mean'),
        (retention_volume, 'RV_sum', 'sum'),
        (infiltration_ratio, 'IR_mean', 'mean'),
        (infiltration_volume, 'IV_sum', 'sum'),
        (retention_value, 'val_sum', 'sum')
    ] + [
        (avoided_pollutant_load, f'')
    ]


    for raster_path, aggregate_field_id, op_type in [
            (l_path, 'qb', 'mean'), (vri_path, 'vri_sum', 'sum')]:

        # aggregate carbon stocks by the new ID field
        aggregate_stats = pygeoprocessing.zonal_statistics(
            (raster_path, 1), aggregate_vector_path)

        aggregate_field = ogr.FieldDefn(aggregate_field_id, ogr.OFTReal)
        aggregate_field.SetWidth(24)
        aggregate_field.SetPrecision(11)
        aggregate_layer.CreateField(aggregate_field)

        aggregate_layer.ResetReading()
        for poly_index, poly_feat in enumerate(aggregate_layer):
            if op_type == 'mean':
                pixel_count = aggregate_stats[poly_index]['count']
                if pixel_count != 0:
                    value = (aggregate_stats[poly_index]['sum'] / pixel_count)
                else:
                    LOGGER.warning(
                        "no coverage for polygon %s", ', '.join(
                            [str(poly_feat.GetField(_)) for _ in range(
                                poly_feat.GetFieldCount())]))
                    value = 0.0
            elif op_type == 'sum':
                value = aggregate_stats[poly_index]['sum']
            poly_feat.SetField(aggregate_field_id, float(value))
            aggregate_layer.SetFeature(poly_feat)

    aggregate_layer.SyncToDisk()
    aggregate_layer = None
    gdal.Dataset.__swig_destroy__(aggregate_vector)
    aggregate_vector = None

    




