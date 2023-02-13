#!/usr/bin/env python
# coding: utf-8

import json
from glob import glob
import pandas as pd
import numpy as np
import os
import tempfile
import shutil
import re
import logging

# configure logging
logging.basicConfig(
    level=logging.INFO, 
    filename='bc_prep_log.log',
    format='%(asctime)s - %(message)s',
    datefmt='%d-%b-%y %H:%M:%S'
)

def mc_2_ep_epp(mc_file):
    # assumption: master curve are saved by default numpy.savetxt with MPa as modulus unit
    mc = np.loadtxt(mc_file)
    # get name for ep and epp
    ep_file = os.path.splitext(mc_file)[0] + '_ep.csv'
    epp_file = os.path.splitext(mc_file)[0] + '_epp.csv'
    # save ep
    np.savetxt(ep_file, mc[:,:2], header="""Frequency (Hz),E' (MPa)""",delimiter=',',comments='')
    np.savetxt(epp_file, mc[:,[0,2]], header="""Frequency (Hz),E" (MPa)""",delimiter=',',comments='')
    return {'ep':ep_file, 'epp':epp_file}

# move and rename files
def mv_rename_file(filename, dest_folder):
    original_name = filename # save original name
    # figure out the new filename
    # remove leading './' if present
    if filename.startswith('./'):
        filename = filename[2:]
    # replace '/' and '\\' with '_'
    filename = re.sub(r'[\\/]+','_',filename)
    # copy the original file into the new folder with new name
    shutil.copy(original_name, os.path.join(dest_folder, filename))
    # rename by returning the new name, use this function with Series.apply()
    return filename

def update_df_filename(df,dest_folder):
    outdf = df.copy()
    for col,b in df.iloc[0].apply(os.path.exists).items():
        if b:
            outdf[col] = outdf[col].apply(lambda x: mv_rename_file(x,dest_folder))
            print(f"{col} column updated.")
            logging.info(f"{col} column updated.")
    logging.info('update_df_filename() successful.')
    return outdf


def prepare_batch_curation(json_dir, base_dir='./', zip_to='./datafiles.zip', columns_out=None,
                          mapping_to='./sample_mapping.csv'):
    '''base_dir is currently unused.'''
    # default columns_out
    if not columns_out:
        columns_out = ['$SID', '$mtx_ep', '$mtx_epp', '$ParRu', '$ParRv', '$VfFree', '$fil_youngs',
               '$fil_poisson', '$n_layers', '$layer', '$intph_shift', '$intph_l_brd', '$intph_r_brd',
               '$fmin', '$fmax', '$num_freq', '$displacement', '$intph_img', '$pix', '$pnc_mc']
    # read and preprocess df from json
    with open(json_dir,'r') as f:
        full_data = json.load(f)
    # build df
    df = pd.DataFrame.from_dict(full_data,orient='index')
    # collect all master curve
    mcs = df['master_curve'].unique()
    # convert to ep.csv and epp.csv
    mc_map = {mc:mc_2_ep_epp(mc) for mc in mcs}
    # update df with mc_map
    # mtx_ep and mtx_epp
    df['mtx_ep'] = df['master_curve'].apply(lambda x:mc_map[x]['ep'])
    df['mtx_epp'] = df['master_curve'].apply(lambda x:mc_map[x]['epp'])
    # pnc_mc pandas < 1.5.0
    # df['pnc_mc'] = df.index
    # df = df.reset_index(drop=True)
    # pnc_mc pandas >= 1.5.0
    df = df.reset_index(names=['pnc_mc'])
    # n_layers and layer
    df['n_layers'] = df.layers.apply(len)
    df['layer'] = df.layers.apply(lambda x:x[0]) # assume 1 layer
    # SID, temporary, maybe sort the df first
    df['SID'] = df.index
    df['SID'] = df['SID'].apply(lambda x:f"S{x+1}")
    # ParRu and ParRv are radius, in the template, we need diameter
    # double both values
    df['ParRu'] = 2*df['ParRu']
    df['ParRv'] = 2*df['ParRv']
    # batch rename columns
    df = df.rename(columns={col[1:]:col for col in columns_out}, errors="raise")
    # select and order by columns_out
    df = df[columns_out]
    # create temporary directory
    td = tempfile.TemporaryDirectory()
    logging.info('Temporary directory created.')
    # update filenames and copy/paste datafiles to td
    df = update_df_filename(df,td.name)
    # zip everything in temporary directory to zip_to
    shutil.make_archive(zip_to, 'zip', td.name)
    logging.info(f'Files in the temporary directory are archived to {zip_to}.')
    # dump sample mapping table
    df.to_csv(mapping_to,index=False)
    logging.info(f'Sample mapping saved as {mapping_to}.')
    # clean up td
    td.cleanup()
    logging.info('Finished cleaning up the temporary directory.')
    return

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Data preparation from json to batch-curation-ready.")
    parser.add_argument("-j", "--json_dir", required=True, type=str,
        help="The json file that contains all simulation parameters.")
    parser.add_argument("-b", "--base_dir", default='./', type=str,
        help="The root directory of your json file and data folders.")
    parser.add_argument("-e", "--export_dir", default='./bc_prep_export', type=str,
        help="The root directory to export all files generated from this script.")
    parser.add_argument("-z", "--zip_to", default='datafiles.zip', type=str,
        help="Filename for the prepared zip archive for appendix datafiles.")
    parser.add_argument("-c", "--columns_out", default=[
        '$SID', '$mtx_ep', '$mtx_epp', '$ParRu', '$ParRv', '$VfFree', '$fil_youngs',
        '$fil_poisson', '$n_layers', '$layer', '$intph_shift', '$intph_l_brd',
        '$intph_r_brd', '$fmin', '$fmax', '$num_freq', '$displacement', 
        '$intph_img', '$pix', '$pnc_mc'], type=str,nargs='+', 
        help="Special placeholders used in the template file.")
    parser.add_argument("-m", "--mapping_to", default='sample_mapping.csv',
        type=str, help="The file name to dump sample mapping table.")
    parser.add_argument("-t", "--master_template", required=True,
        help="Type the file name of your filled master template.")
    args = parser.parse_args()

    # make the folder for export if not exist
    if not os.path.exists(args.export_dir):
        os.makedirs(args.export_dir)
        logging.info(f'Export directory created at {args.export_dir}')
    # copy the template into the export dir
    shutil.copy(args.master_template,
        os.path.join(args.export_dir,args.master_template))
    logging.info(f'Master template {args.master_template} copied to the export dir.')

    prepare_batch_curation(
        json_dir=args.json_dir,
        base_dir=args.base_dir,
        zip_to=os.path.join(args.export_dir,args.zip_to),
        columns_out=args.columns_out,
        mapping_to=os.path.join(args.export_dir,args.mapping_to),
    )
