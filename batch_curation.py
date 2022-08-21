## By Anqi Lin 08/21/2022

# -------------------------------------------- file os and other general lib
import os
import shutil
import tempfile
from glob import glob
from tqdm import tqdm
# -------------------------------------------- for data I/O
import openpyxl
import pandas as pd
import zipfile

class batch_curation():
    def __init__(self, base_dir, master_template, mapping_tabular,
            zipped_datafiles, output_dir=None):
        '''
        Input:
        :param base_dir: base directory of the master template, mapping tabular 
            file, zipped datafiles.
        :type base_dir: str
        
        :param master_template: file name of the master template. *.xlsx
        :type master_template: str

        :param mapping_tabular: file name of the mapping tabular file.
            *.xlsx/*.csv/*.tsv
        :type mapping_tabular: str
        
        :param zipped_datafiles: file name of the zipped datafiles. *.zip
        :type zipped_datafiles: str

        :param output_dir: directory to output the constructed zip file for
            batch curation. Default to base_dir.
        :type output_dir: str or NoneType
        '''
        self.base_dir_abspath = os.path.abspath(base_dir)
        self.master_template_abspath = os.path.abspath(os.path.join(base_dir,
            master_template))
        self.zipped_datafiles_abspath = os.path.abspath(zipped_datafiles)
        self.master_template_name = 'master_template.xlsx' # default name
        self.output_dir = os.path.join(self.base_dir_abspath,
            'batch_template_output') if output_dir is None else output_dir
        # trim .zip
        if self.output_dir[-4:] == '.zip':
           self.output_dir = self.output_dir[:-4]
        # load mapping
        self.df = self.read_mapping(self.base_dir_abspath, mapping_tabular)
        # run
        self.run()

    def read_mapping(self, base_dir, mapping_tabular):
        ## Read sample-variable mapping
        file_ext = os.path.splitext(mapping_tabular)[1].lower()
        # Excel file
        if file_ext == '.xlsx':
            df = pd.read_excel(os.path.join(base_dir,mapping_tabular))
        # csv file
        elif file_ext == '.csv':
            df = pd.read_csv(os.path.join(base_dir,mapping_tabular))
        # tsv file
        elif file_ext == '.tsv':
            df = pd.read_csv(os.path.join(base_dir,mapping_tabular),sep='\t')
        else:
            raise Exception('The mapping file must be a .xlsx/.csv/.tsv file.')
        return df

    def run(self):
        # create temporary directory
        with tempfile.TemporaryDirectory() as td:
            self.tempdir = td
            # extract zip files
            self.extracted_datafiles_abspath = os.path.join(self.tempdir,
                'zipped_datafiles')
            os.mkdir(self.extracted_datafiles_abspath)
            # move into the temporary directory
            os.chdir(self.tempdir)

            # extract data files
            appendix = zipfile.ZipFile(self.zipped_datafiles_abspath)
            appendix.extractall(self.extracted_datafiles_abspath)
            # for each sample, call run_sample to create the sample folder and move
            # corresponding files into it and modify as needed
            for idx,sample in tqdm(self.df.iterrows(), total=self.df.shape[0]):
                self.run_sample(sample)
            # remove extracted data files
            shutil.rmtree(self.extracted_datafiles_abspath)
            # zip the files in the temporary folder into a zip file self.output_dir
            shutil.make_archive(self.output_dir, 'zip', self.tempdir)

    def run_sample(self, sample_mapping):
        # create a folder for each sample using sample id as the name
        # assume sample id is always the first item in sample_mapping
        sample_folder = os.path.join(self.tempdir,sample_mapping[0])
        os.mkdir(sample_folder)
        # copy and paste the master template into the folder
        shutil.copy(self.master_template_abspath,
            os.path.join(sample_folder,self.master_template_name))
        # update the master template
        self.update_template(sample_folder, self.master_template_name,
            sample_mapping)
        # copy and paste the appendix datafiles into the folder
        for file in sample_mapping:
            if isinstance(file,str) and \
            os.path.exists(os.path.join(self.extracted_datafiles_abspath,file)):
                shutil.copy(os.path.join(self.extracted_datafiles_abspath,file),
                    os.path.join(sample_folder,file))

    ## Modify master template in place
    def update_template(self, base_dir, master_template, sample_mapping):
        '''
        Input:
        :param sample_mapping: a row in the mapping DataFrame
        :type sample_mapping: pandas.Series
        '''
        wb = openpyxl.load_workbook(os.path.join(base_dir,master_template))
        ignore_sheets = {'legend','4. Characterization Methods',
            'Characterization Methods to Add','Dropdown menu choices'}
        for sheet in wb:
            # ignore irrelevant worksheets
            if sheet.title in ignore_sheets:
                continue
            # since col 1 is always property names, we can skip it
            for row in sheet.iter_rows(min_col=2):
                for cell in row:
                    if isinstance(cell.value,str) and cell.value.startswith('$'):
                        cell.value = sample_mapping[cell.value]
        wb.save(os.path.join(base_dir,master_template))



if __name__ == '__main__':
    base_dir = './example'
    mapping = 'example_mapping.xlsx'
    template = 'example_template.xlsx'
    zipped_datafiles = 'example.zip'
    bc = batch_curation(base_dir=base_dir, master_template=template,
        mapping_tabular=mapping,zipped_datafiles=zipped_datafiles)