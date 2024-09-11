# Really I will fill in the important comments later

# Comments on server naming conventions and what we can assume:
# State office server_name: aioorpo23fp1
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
import arcpy


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
date_stamp = datetime.datetime.now().strftime("_%Y%m")

# To avoid hard-coded strings everywhere
mdb = ".mdb"
shp = ".shp"

prefixes = {mdb: "soil_d_", shp: "soilmu_a_"}


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

    # shps don't need flattening, so this is their original location
    shp_dir = Path(get_root(mothership), "geodata", "soils")

    mothership_dirs = {"download": download_dir, mdb: mdb_dir, shp: shp_dir}

    # Print All The Things to make sure our output is what we expect
    print("\nOutput of get_mothership_dirs() (var mothership_dirs):")
    for k, v in mothership_dirs.items():
        print(f"\tKey: {k}, value: {v}")

    return mothership_dirs


########## ########## ########## 

# Walk the dir where all the mdbs are scattered among various subfolders
# and consolidate them into one dir
def consolidate_mdbs(mothership_dirs):

    # Make the new FY dir if it does not already exist
    os.makedirs(mothership_dirs[mdb], exist_ok= True)

    # [0] is the downloads dir
    for root, dirs, files in os.walk(mothership_dirs["download"]):

        # Can't iterate files that aren't there
        if not files:
            continue

        # Otherwise (if there are files), iterate
        for fi in files:

            if fi.endswith(mdb) and fi.startswith(prefixes[mdb]):

                # Full path to the file I want to consolidate
                from_path = Path(root, fi)

                to_path = Path(mothership_dirs[mdb], f"{fy_stamp}.".join(fi.rsplit(".", 1)))

                # Do the copy thing
                try:
                    shutil.copy(from_path, to_path)

                # YES I KNOW...will expand later
                except Exception as e:
                    print(e)



########## ########## ########## 

def get_filepaths(mothership_dirs):

    # Initialize a dict of dicts
    filepaths = {mdb: {}, shp: {}}

    for k, v in mothership_dirs.items():

        # We don't need to get full filepaths for the original downloads dir
        if k == "download":
            continue

        # I don't need to do anything more with the mdbs since they've 
        # already been FY-stamped when they were consolidated
        elif k == mdb:

            # Make a list of the full paths of the mdb files to be copied
            prepaths = [str(Path(v, f)) for f in os.listdir(v) if f.endswith(k)]

            # Now I need that 5-char code within these preprepaths to use
            # as the key to the list of all the filepaths
            for p in prepaths:

                # Chop it at "soil_d_"
                chop = p.split(prefixes[mdb])

                # If it had "soil_d_" in it...
                if len(chop) > 1:

                    # ...Stuff the full filepath in a list as a value in a dict
                    # where the 5-char code is the key; this facilitates easy lookup later
                    filepaths[k][chop[1][:5]] = [p]

        elif k == shp:

            # NOTE: THIS GETS ALL THE FILES IN THE DIRECTORY...
            preprepaths = [str(Path(v, f)) for f in os.listdir(v) if prefixes[shp] in f]

            prepaths = []

            # But for shps we still need to apply our datestamp...
            for p in preprepaths:

                # If the file hasn't already been datestamped, stamp it
                if not date_stamp in p:

                    # Of course the xml file has to be the special snowflake
                    # with two periods and two go#dam# extensions...
                    if p.endswith(".xml"):
                        
                        # The "fake" period in the xml always preceeds .shp, sooo:
                        dated = f"{date_stamp}.shp".join(p.rsplit(shp, 1))

                    else:
                        # Chop up the path, add in the date stamp and zip it back up again
                        # This of course just builds the correct string...
                        dated = f"{date_stamp}.".join(p.rsplit(".", 1))

                    # ...Can't forget to actually rename the file itself
                    os.replace(p, dated)

                # Otherwise if the file already has the datestamp, it's all good
                else:
                    dated = p

                prepaths.append(dated)
            
            for p in prepaths:

                # Chop it at "soilmu_a_"
                chop = p.split(prefixes[shp])

                # If it had "soilmu_a_" in it...
                if len(chop) > 1:

                    # Assign 5-char code to var
                    # since there's way too much crap going on here
                    key_code = chop[1][:5]

                    # ...Stuff the full filepath in a list as a value in a dict
                    # where the 5-char code is the key; this facilitates easy lookup later
                    # If the key code isn't already in the dict, add and add the first full path
                    # as first item in the list that is the val
                    if not key_code in filepaths[k]:
                        filepaths[k][key_code] = [p]

                    # If the key code is already in the dict, append this file path
                    # to list located at this key
                    else:
                        filepaths[k][key_code].append(p)


    # Print All The Things to make sure our output is what we expect
    print(f"\nOutput of get_filepaths (var filepaths):")

    for k, val in filepaths.items():
        print(f"\tKey: {k}, Values:")
        for x, y in val.items():
            print(f"\t\tSubkey: {x}, Values:")
            for x in y:
                print(f"\t\t\t{x}")
                  
    return filepaths


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

    # Assumes that for the Real Deal the satellite host names come from
    # either a feature class or feature service URL
    # TO DO...figure out why import of arcpy is not working,
    # even if ArcGIS Pro is open etc.
    else:

        search_field = "name_of_the_field"

        satellite_list = [row[0] for row in arcpy.da.SearchCursor(satellite_source, search_field)]

        # We are copying FROM mothership so exclude her
        # from the list of copy TO hosts
        if mothership in satellite_list:
            satellite_list.remove(mothership)

    # Print All The Things to make sure our output is what we expect
    print("\nOutput of get_satellites (satellite_list):")
    for s in satellite_list:
        print(f"\t{s}")

    return satellite_list



########## ########## ########## 

def get_satellite_dirs(satellite):

    mdb_dir = Path(get_root(satellite), "FOTG", "Section_II")

    shp_dir = Path(get_root(satellite), "geodata", "soils")

    satellite_dirs = {mdb: mdb_dir, shp: shp_dir}

    print(f"\nOutput of get_satellite_dirs({satellite}):")
    for k, v in satellite_dirs.items():
        print(f"\tKey: {k}, value: {v}")

    return satellite_dirs



########## ########## ########## 

# Figure out which fo need which files
def get_sat_required(satellite_dirs, sat):

    sat_required = {}

    for k, v in satellite_dirs.items():

        current_files = [f for f in os.listdir(v) if f.endswith(k)]

        if k == mdb:
            filtered_list = [f for f in current_files if f.startswith(prefixes[mdb])]

            sat_required[k] = set([str(f.split(prefixes[mdb])[1][:5]) for f in filtered_list])
            
        elif k == shp:
            filtered_list = [f for f in current_files if f.startswith(prefixes[shp])]

            sat_required[k] = set([str(f.split(prefixes[shp])[1][:5]) for f in filtered_list])

    # Print All The Things to make sure our output is what we expect
    print(f"\nOutput of get_sat_required {sat}:")
    for k, v in sat_required.items():
        print(f"\tKey: {k}, value: {v}")

    return sat_required



########## ########## ########## 

def archive_old(satellite_dirs, ext):
    
    # Construct the path to the "Old to delete" dir
    # This is a subfolder within the dir
    # to which we want to copy the new files
    archive = Path(satellite_dirs[ext], "Old to Delete")

    # If it exists (as it should), delete it and all files in it
    if os.path.exists(archive):
        shutil.rmtree(archive)

    # Then remake it so it's a fresh folder w/no files in it
    os.makedirs(archive, exist_ok=True)

    # For all the files in the current directory
    # (Do I need to narrow this down at all...?)
    current_files = os.listdir(satellite_dirs[ext])

    # Iterate through all the files currently in our working dir
    for c in current_files:

        # Construct the string for where the existing file
        move_path = Path(satellite_dirs[ext], c)

        # Construct the string for the future archived file
        moved_path = Path(satellite_dirs[ext], archive, c)

        # If it isn't a file (i.e. if it's a dir) don't touch it
        if not os.path.isfile(move_path):
            continue

        # Otherwise move it to the archive
        shutil.move(move_path, moved_path)



########## ########## ########## 

def copy_file(in_file, to_dir):

    #try:
        #arcpy.management.Copy(in_file, out_file)

    # YES I KNOW...will expand later
    #except Exception as e:
        #print(e)

    try:
        shutil.copy(in_file, to_dir)

    # YES I KNOW...will expand later
    except Exception as e:
        print(e)



########## ########## ########## 

# Iterate through all the  satellite field office servers,
# generate lists of the specific files they need if applicable,
# Then copy the appropriate files
def iter_satellites(mothership_filepaths, satellite_list):

    for sat in satellite_list:

        # Rest of this script assumes we get the full server host name here
        satellite_dirs = get_satellite_dirs(sat)

        # Get the list of 5-char codes ALREADY IN the dirs...
        sat_required = get_sat_required(satellite_dirs, sat)

        # Iterate through the 5-char codes in the dest dir
        for ext, code_list in sat_required.items():

            # Archive any files currently in the destination dir
            archive_old(satellite_dirs, ext)

            # For each 5-char code
            for code in code_list:

                # For each individual file containing that 5-char code
                # (This iters once for mdbs, but multiple times for shps)
                for path in mothership_filepaths[ext][code]:

                    # Do the thing
                    copy_file(path, satellite_dirs[ext])



########## ########## ########## ########## ########## ########## 

# DO THE THING
# I.E. ALL THE CALLS

mothership_dirs = get_mothership_dirs()

consolidate_mdbs(mothership_dirs)

mothership_filepaths = get_filepaths(mothership_dirs)

satellite_list = get_satellites(satellite_source)

iter_satellites(mothership_filepaths, satellite_list)

