# nm_curation_batch_template_generation
Batch master template generation for batch curation of computational (FEA/MD) data into NanoMine.

### Input
1. A tabular file that lists values of varying parameters for each sample to be curated. The first column should be the sample id, the first row should be the set of special placeholders, e.g. *$sample_id*, *$intph_thick*, etc. See example/example_mapping.csv for reference.
2. A master template with cells that do not change among the samples filled with values, and cells that change filled with the corresponding special placeholders as described above. See example/example_template.xlsx for reference.
3. A zip file that contains the master template as described in 2. and all required datafiles. See example/example.zip for reference.

### Output
1. A zip file that is constructed with the following structure:

<pre>output.zip
  ∟ $sample_id1
    ∟ master_template.xlsx
    ∟ appendix_1.csv
    ∟ appendix_2.mat
    ∟ appendix_3.inp
    ...
  ∟ $sample_id2
    ∟ master_template.xlsx
    ∟ appendix_1.csv
    ∟ appendix_2.mat
    ∟ appendix_3.inp
    ...
  ... </pre>
