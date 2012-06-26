#!/usr/bin/python
# File created on 09 Feb 2010
from __future__ import division

__author__ = "Meg Pirrung"
__copyright__ = "Copyright 2011, The QIIME Project"
__credits__ = ["Meg Pirrung", "Jesse Stombaugh"]
__license__ = "GPL"
__version__ = "1.4.0"
__maintainer__ = "Jesse Stombaugh"
__email__ = "jesse.stombaugh@colorado.edu"
__status__ = "Release"
 
from qiime.util import make_option
from qiime.util import parse_command_line_parameters, get_qiime_project_dir, \
                       create_dir,get_options_lookup
from cogent.util.misc import get_random_directory_name
from sys import argv, exit, exc_info
from qiime.colors import sample_color_prefs_and_map_data_from_options
from qiime.parse import parse_rarefaction_data,parse_rarefaction
from qiime.make_rarefaction_plots import make_averages
from os.path import exists, splitext, split,isdir
from os import listdir,path

options_lookup = get_options_lookup()

script_info={}
script_info['brief_description']="""Generate Rarefaction Plots"""
script_info['script_description']="""Once the batch alpha diversity files have been collated, you may want to compare the diversity using plots. Using the results from collate_alpha.py, you can plot the samples and or by category in the mapping file using this script.

This script creates an html file of rarefaction plots based on the supplied collated alpha-diversity files in a folder or a comma-separated list of files, by passing the "-i" option.  Be aware that this script produces many images for the interactive html pages, so you may choose to not create these pages. The user may also supply optional arguments like an image type (-g), and a resolution (-d)."""
script_info['script_usage']=[]
script_info['script_usage'].append(("""Default Example:""","""For generated rarefaction plots using the default parameters, including the mapping file and one rarefaction file, you can use the following command:""","""make_rarefaction_plots.py -i collated_alpha/ -m mapping_file.txt"""))
script_info['script_usage'].append(("""Specify Image Type and Resolution:""","""Optionally, you can change the resolution ("-d") and the type of image created ("-i"), by using the following command:""","""make_rarefaction_plots.py -i collated_alpha/ -m mapping_file.txt -d 180 -g pdf"""))
script_info['script_usage'].append(("""Use Prefs File:""","""You can also supply a preferences file "-p", as follows""","""make_rarefaction_plots.py -i collated_alpha/ -m mapping_file.txt -d 180 -p prefs.txt"""))
script_info['script_usage'].append(("""Set Background Color:""","""Alternatively, you can set the plot background "-k", as follows: a preferences file "-p", as follows""","""make_rarefaction_plots.py -i collated_alpha/ -m mapping_file.txt -k black"""))
script_info['script_usage'].append(("""Generate raw data without interactive webpages:""","""The user can choose to not create an interactive webpage ("-w" option).  This is for the case, where the user just wants the average plots and the raw average data.""","""make_rarefaction_plots.py -i collated_alpha/ -m mapping_file.txt -w"""))
script_info['output_description']="""The result of this script produces a folder and within that folder there is a sub-folder containing image files. Within the main folder, there is an html file."""
script_info['required_options']=[\
    make_option('-i', '--input_dir', 
        help='Input directory containing results from collate_alpha.py.' +\
        ' [REQUIRED]',
        type='existing_dirpath'),
    make_option('-m', '--map_fname', 
        help='Input metadata mapping filepath. [REQUIRED]',
        type='existing_filepath')
]
script_info['optional_options']=[\
    make_option('-b', '--colorby', dest='colorby',\
        help='Comma-separated list categories metadata categories' +\
        ' (column headers) ' +\
        'to color by in the plots. The categories must match the name of a ' +\
        'column header in the mapping file exactly. Multiple categories ' +\
        'can be list by comma separating them without spaces. The user can ' +\
        'also combine columns in the mapping file by separating the ' +\
        'categories by "&&" without spaces. [default=color by all]'),
    make_option('-p', '--prefs_path',
        help='Input user-generated preferences filepath. NOTE: This is a' +\
        ' file with a dictionary containing preferences for the analysis.' +\
        ' [default: %default]',
        type='existing_filepath'),
    make_option('-k', '--background_color', 
        help='Background color to use in the plots' +\
        '[default: %default]',default='white', 
        type='choice',choices=['black','white'],),
    make_option('-g', '--imagetype',
        help='Type of image to produce (i.e. png, svg, pdf).' +\
        ' WARNING: Some formats may not properly open in your browser!' +\
        ' [default: %default]', default='png',type="choice",
        choices=['png','pdf','svg']),
    make_option('-d', '--resolution', 
        help='Resolution of the plot. [default: %default]', 
        type='int', default=75),
    make_option('-y', '--ymax', type='int', 
        help='Maximum y-value to be used for the plots. Allows' +\
        ' for directly comparable rarefaction plots between analyses' +\
        ' [default: %default]'),
    make_option('-w', '--webpage', action='store_false', 
        help='DEPRECATED: Suppress HTML output. [default: %default]',
         default=True),
    make_option('-s','--suppress_html_output', action='store_true', 
         help='Suppress HTML output. [default: %default]', default=False),
    make_option('-e','--std_type',default='stddev',type="choice",
         help='Calculation to perform for generating error bars. Options '+\
         'are standard deviation (stddev) or standard error (stderr). '+\
         '[default: %default]', choices=['stddev','stderr']),
    options_lookup['output_dir']
]
script_info['option_label']={'input_dir':'Collated alpha-diversity directory',
                             'map_fname':'QIIME-formatted mapping filepath',
                             'colorby': 'Colorby category',
                             'output_dir': 'Output directory',
                             'prefs_path': 'Preferences filepath',
                             'imagetype': 'Image type',
                             'resolution':'Image resolution',
                             'ymax': 'Y-axis height',
                             'webpage':'Suppress HTML (Deprecated)',
                             'suppress_html_output':'Suppress HTML'}
                             
script_info['version'] = __version__

def main():
    option_parser, options, args = parse_command_line_parameters(**script_info)
      
    ops = {}
    input_dir = options.input_dir

    rares = {}
    if isdir(input_dir):
        rarenames = listdir(input_dir)
        rarenames = [r for r in rarenames if not r.startswith('.')]
        for r in rarenames:
            try:
                 rarefl = open(path.join(input_dir,r), 'U').readlines()
                 rares[r] = parse_rarefaction(rarefl)
            except(IOError):
                option_parser.error('Problem with rarefaction file. %s'%\
                exc_info()[1])
                exit(0)
    else:
        try:
             input_file=input_dir.split(',')
             for i in range(len(input_file)):
                 input_path=split(input_file[i])[-1]
                 rarefl = open(input_file[i], 'U').readlines()
                 rares[input_path] = parse_rarefaction(rarefl)
        except(IOError):
            option_parser.error('Problem with rarefaction file. %s'%\
            exc_info()[1])
            exit(0)
    if options.imagetype not in ['png','svg','pdf']:
        option_parser.error('Supplied extension not supported.')
        exit(0)
    else:
        imagetype = options.imagetype
        
    try:
        resolution = int(options.resolution)
    except(ValueError):
        option_parser.error('Inavlid resolution.')
        exit(0)
    
    #Get the command-line options.
    prefs, data, background_color, label_color, ball_scale, arrow_colors = \
                    sample_color_prefs_and_map_data_from_options(options)
    
    #output directory check
    if isinstance(options.output_dir, str) and options.output_dir != '.':
        if exists(options.output_dir):
            output_dir = options.output_dir
        else:
            try:
                create_dir(options.output_dir,False)
                output_dir = options.output_dir
            except(ValueError):
                option_parser.error('Could not create output directory.')
                exit(0)
    else:
        output_dir = get_random_directory_name()
    
    #Generate the plots and html text
    ymax=options.ymax
    std_type=options.std_type
    suppress_webpage=options.suppress_html_output
    html_output = make_averages(prefs, data, background_color, label_color, \
                                rares, output_dir,resolution,imagetype,ymax,
                                suppress_webpage,std_type)
                                
    if html_output:
        #Write the html file.
        outfile = open(path.join(output_dir,'rarefaction_plots.html'),'w')
        outfile.write(html_output)
        outfile.close()


if __name__ == "__main__":
    main()