# Really I will fill in the important comments later

# Comments on server naming conventions and what we can assume:
# Example server_name: aioorpo23fp1
# aio | or | po2 | 3fp1
# Prefix (always the same): server_name[:3] = "aio"
# State abbr: server_name[3:5] = "or"
# Office abbr, 3 digits: server_name[5:8] = "po2" (Portland office 2; there are 3 total)
# Random last 4 digits (/what does it mean??/): server_name[8:] = "3fp1"
    # Alt: server_name[-3:] = "3fp1"


########## ########## ########## ########## ########## ########## 
# IMPORTS

import os
from pathlib import Path
import datetime
import shutil
#import arcpy


########## ########## ########## ########## ########## ########## 
# INPUT PARAMETERS
# These could be exposed in e.g. python toolbox

# Switch to control whether this is run on UNCs or letter dr
# (Construction of path for each is slightly different)
test_local = True

if test_local:
    # For testing - local letter drive alt mothership source
    mothership = r"C:\Users\misti.wudtke\OneDrive - USDA\PYTHON\NRCSPY\copy_soils\working_dir\_F"
    satellite_source = os.path.dirname(mothership)

else:
    # Non-testing mode assumes data is accessed via UNC \\host\share
    mothership = "aioorpo23fp1"
    satellite_source = "table_source" # REPLACE!!!!!!!!

# FY stamp to append to MDBs
fy_stamp = "_FY24"



########## ########## ########## ########## ########## ########## 
# NON-INPUT PARAMETERS

# Provides datestamp string in the format of "_YYYYMMDD", ready to append
date_stamp = datetime.datetime.now().strftime("_%Y%m%d")

# List to hold all the dirs that we need to clean up for testing
cleanup_list = []



########## ########## ########## ########## ########## ########## 
# FUNCTIONS

def get_root(field_office):

    if test_local:
        root = Path(satellite_source, field_office, "data")

    else:
        root = f"\\\\{field_office}\\data"

    return root



########## ########## ########## 

def get_mothership_dirs():

    download_dir = Path(get_root(mothership), "download")
    
    # Path to intermediate mdb testination
    # (after flattening, before doling to FOs)
    mdb_dir = Path(get_root(mothership), "FOTG", "Section_II", "FY24")

    # Since we'll be copying TO this dir, needs to be
    # cleaned up regularly during testing
    cleanup_list.append(mdb_dir)

    # shps don't need flattening, so this is their original location
    shp_dir = Path(get_root(mothership), "geodata", "soils", "FY24")

    mothership_dirs = {"download": download_dir, ".mdb": mdb_dir, ".shp": shp_dir}

    return mothership_dirs



########## ########## ########## 

def copy_file(in_file, to_dir):

    # TO DO: the Thing.
    try:
        shutil.copy(in_file, to_dir)

    # YES I KNOW...will expand later
    except Exception as e:
        print(e)



########## ########## ########## 

# Walk the dir where all the mdbs are scattered among various subfolders
# and consolidate them into one dir
def consolidate_mdbs(mothership_dirs):

    # [0] is the downloads dir
    for root, dirs, files in os.walk(mothership_dirs["download"]):

        if files:
            for f in files:

                # TO DO: additional logic here to narrow down search!
                if f.endswith(".mdb"):
                    fullpath = os.path.join(root, f)

                    copy_file(fullpath, mothership_dirs[".mdb"])



########## ########## ########## 

def get_filepaths(mothership_dirs):

    filepaths_dict = {}

    for k, v in mothership_dirs.items():

        # We don't need to get full filepaths for the original downloads dir
        if k == "download":
            continue

        filepaths_dict[k] = [Path(v, f) for f in os.listdir(v) if f.endswith(k)]

    return filepaths_dict



########## ########## ########## 

# Get a list of all field office server names...from somewhere
def get_satellites(satellite_source):

    # Test local flavor of this involves getting the list of folder names
    # that correspond to the various field offices (e.g. _field_office_1)
    if test_local:
        
        satellite_list = [f for f in os.listdir(satellite_source)]

        # We are copying FROM mothership so exclude her
        # from the list of copy TO dirs
        m = os.path.basename(mothership)
        if m in satellite_list:
            satellite_list.remove(m)

        # TO DO: an else statement here because the mothership SHOULD
        # be among the satellites in the heirarchy

    # Assumes that for the Real Deal the satellite host names come from
    # either a feature class or feature service URL
    else:

        search_field = "name_of_the_field"

        satellite_list = [row[0] for row in arcpy.da.SearchCursor(satellite_source, search_field)]

        # We are copying FROM mothership so exclude her
        # from the list of copy TO hosts
        if mothership in satellite_list:
            satellite_list.remove(mothership)

        # TO DO: an else statement here because the mothership SHOULD
        # be among the satellites in the heirarchy

    return satellite_list



########## ########## ########## 

def get_satellite_dirs(satellite):

    mdb_dir = Path(get_root(satellite), "FOTG", "Section_II")

    shp_dir = Path(get_root(satellite), "geodata", "soils")

    satellite_dirs = {".mdb": mdb_dir, ".shp": shp_dir}

    print(satellite_dirs)

    return satellite_dirs



########## ########## ########## 

def get_sat_required():

    sat_required = []

    # TO  DO: figure out which fo need which files
    # MAKE SURE TO COPY NEW FILES FIRST BEFORE DELETING OLD


    # ***** YOU ARE HERE ***** 
    # ***** YOU ARE HERE ***** 
    # ***** YOU ARE HERE ***** 

    return sat_required



########## ########## ########## 

# Iterate through all the  satellite field office servers,
# generate lists of the specific files they need if applicable,
# Then copy the appropriate files
def iter_satellites(mothership_filepaths, satellite_list, cleanup_list):

    for sat in satellite_list:

        # TO DO: all the things

        # Rest of this script assumes we get the full server host name here
        satellite_dirs = get_satellite_dirs(sat)

        # Toss in the satellite directories as we iter through them
        for v in satellite_dirs.values():
            cleanup_list.append(v)

        # TO DO: get the list of files ALREADY IN the dirs...
        # back-burnering this for now in favor of just getting the file copying working
        sat_required = get_sat_required()

        for extension, path_list in mothership_filepaths.items():
            for path in path_list:
                if path in sat_required:
                    continue
                copy_file(path, satellite_dirs[extension])

    return cleanup_list



########## ########## ########## ########## ########## ########## 

# DO THE THING
# I.E. ALL THE CALLS

mothership_dirs = get_mothership_dirs()

consolidate_mdbs(mothership_dirs)

mothership_filepaths = get_filepaths(mothership_dirs)

satellite_list = get_satellites(satellite_source)

cleanup_list = iter_satellites(mothership_filepaths, satellite_list, cleanup_list)

