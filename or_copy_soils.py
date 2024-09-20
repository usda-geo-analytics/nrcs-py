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

# Built in a means to test retrieval of all field office host names from table service
# Just replace this URL with URL to table service (including layer index!)
satellite_table = r"https://services.arcgis.com/LLVEmB8Lsae3Um4s/arcgis/rest/services/NRCS_CopySoils_FieldOffices/FeatureServer/0"

# Testing switch uses letter drives vice UNC paths (because I don't
# have access to the collection of hosts this would actually be run against)
if test_local:

    # This dir is only ever referenced for testing
    test_dir = r"C:\Users\misti.wudtke\OneDrive - USDA\PYTHON\NRCSPY\copy_soils\working_dir"

    # For testing "mothership" is just the name of a dir
    mothership = "_F"


# Unfortunately I don't have a way to test this funcitonality yet
else:

    # Outside of testing, "mothership" is the host of a \\host\share UNC
    mothership = "aioorpo23fp1"

# FY stamp to append to MDBs
fy_stamp = "_FY24"



########## ########## ########## ########## ########## ########## 
# NON-INPUT PARAMETERS

# Provides datestamp string in the format of "_YYYYMMDD", ready to append
date_stamp = datetime.datetime.now().strftime("_%Y%m")

# To avoid hard-coded strings everywhere
mdb = ".mdb"
shp = ".shp"

# Non-hard-coded way to refer to appropriate filename prefixes where appropriate
prefixes = {mdb: "soil_d_", shp: "soilmu_a_"}


########## ########## ########## ########## ########## ########## 
# FUNCTIONS

# Generate full path up to "data" dir for either mothership or satellite offices
# Need to go up to "data" dir because for UNC (i.e. non-test) runs,
# "Path" only works with full "\\host\share" path and "data" is the share
def get_root(field_office):

    if test_local:
        root = Path(test_dir, field_office, "data")

    else:
        root = f"\\\\{field_office}\\data"

    return root



########## ########## ########## 

# This returns a dictionary with three k/v pairs;
# Keys are strs: "download", "mdb" and "shp"
# "download" value is the dir we need to walk to get all (preexisting) mdbs;
# "mdb" value is the dir where consolidated mdbs are put (by this script),
# and "shp" is the dir where (preexisting) shps live
# Dict with extensions as keys is consistent across multiple functions
# throughout script and provides intuitive access to appropriate dirs
def get_mothership_dirs():

    # Get path where the downloads live
    download_dir = Path(get_root(mothership), "download")
    
    # Get path to intermediate mdb testination
    # (after consolidation, before doling to satellite FOs)
    mdb_dir = Path(get_root(mothership), "FOTG", "Section_II", "FY24")

    # shps don't need flattening, so this is their original location
    shp_dir = Path(get_root(mothership), "geodata", "soils")

    # Assemble the dictionary
    mothership_dirs = {"download": download_dir, mdb: mdb_dir, shp: shp_dir}

    # Print All The Things to make sure our output is what we expect
    print("\nOutput of get_mothership_dirs() (var mothership_dirs):")
    for k, v in mothership_dirs.items():
        print(f"\tKey: {k}, value: {v}")

    return mothership_dirs



########## ########## ########## 

# Walk the dir where all the mdbs are scattered among various subfolders
# and consolidate them into one "flat" dir
def consolidate_mdbs(mothership_dirs):

    # Make the new consolidated FY dir if it does not already exist
    os.makedirs(mothership_dirs[mdb], exist_ok= True)

    # Walk the dir where all the mdb files currently reside (among various subfolders)
    for root, dirs, files in os.walk(mothership_dirs["download"]):

        # Can't iterate files that aren't there
        if not files:
            continue

        # Otherwise (if there are files), iterate
        for fi in files:

            if fi.endswith(mdb) and fi.startswith(prefixes[mdb]):

                # Full path to the file I want to consolidate
                from_path = Path(root, fi)

                # Build path for new file: new dir + file name head + fy_stamp + file name tail
                to_path = Path(mothership_dirs[mdb], f"{fy_stamp}.".join(fi.rsplit(".", 1)))

                # Try the copy thing
                try:
                    shutil.copy(from_path, to_path)

                # If it didn't work, deal with that it didn't work
                # (I will expand/fix this block I swear)
                except Exception as e:
                    print(e)



########## ########## ########## 

# Returns a dictionary meant to provide easy access to filepaths later
# Keys are the 5-char code, derived from the filepath itself,
# and the value is the entire file path. This provides the means to look up
# and use the full file path based on the 5-char code
def get_mdb_filepaths(mdb_dir):

    # Create the empty dict to hold everything
    mdb_filepaths = {}

    # Make a list of ALL filepaths to ALL MDB files w/in our consolidated dir
    prepaths = [str(Path(mdb_dir, f)) for f in os.listdir(mdb_dir) if f.endswith(mdb)]

    # Now we construct the keys to the dict based on the values;
    # technically the dict key is a substring of its value.
    for p in prepaths:

        # Chop up the string at the prefix we expect to see for mdbs
        chop = p.split(prefixes[mdb])

        # If it had the prefix (i.e. if it's a filepath we want), 
        # length of the resulting list will be > 1
        if len(chop) > 1:

            # The key is the first 5 digits of the 2nd item in the list "chop",
            # Stuff that in the dict as the key and add the full path as the corresponding value.
            # Note that we're adding the filepath as a single item in a list.
            # This is all the fault of @sshole shapefiles; see comments
            # toward the end of get_shp_filepaths function
            mdb_filepaths[chop[1][:5]] = [p]

    return mdb_filepaths



########## ########## ########## 

# This function applies datestamps to shapefiles,
# First by building the appropriate strings
# then actually renaming the files
def apply_datestamps(preprepaths):

    # Empty list to hold pre-filepaths
    prepaths = []

    # Iterate PRE-pre-paths (which are the preexisting files)
    for p in preprepaths:

        # If the file hasn't already been datestamped, stamp it
        if not date_stamp in p:

            # Of course the xml file has to be the special snowflake
            # with two periods and two go#dam# extensions...
            if p.endswith(".xml"):
                
                # The "fake" period in the xml always preceeds .shp, sooo:
                dated = f"{date_stamp}.shp".join(p.rsplit(shp, 1))

            # For non-XML files, just slice & dice name and cram in the datestamp...
            # ...this of course just builds the correct string...
            else:
                dated = f"{date_stamp}.".join(p.rsplit(".", 1))

            # ...Can't forget to actually rename the file itself
            os.replace(p, dated)

        # Otherwise if the file's already stamped, carry on
        else:
            dated = p

        # Add the datestamped file path string to our list
        prepaths.append(dated)

    return prepaths



########## ########## ########## 

# Returns a dictionary of shapefile filepaths
# Where the key is the 5-char code that is a substring of the full path,
# The 5-char code is used to look up and copy filepaths later based on
# whether a given field office needs the file associated with that 5-char code
def get_shp_filepaths(shp_dir):

    # Initialize the empty dict
    shp_filepaths = {}

    # Build the list of all shapefiles in the mothership shp dir
    # Note that we're not checking file extensions / endswith() here!
    # Not sure if that could be an issue or not; for the time being
    # we are assuming that shapefile components are the ONLY ITEMS 
    # that will be found in this directory
    preprepaths = [str(Path(shp_dir, f)) for f in os.listdir(shp_dir) if prefixes[shp] in f]

    # Do the apply_datestamps boogie
    prepaths = apply_datestamps(preprepaths)

    # Once we have the prepaths, shuffle everything into the dict we have ready
    for p in prepaths:

        # Chop each path at the filename prefix we expect for shps
        # (the 5-char code is immeidately adjacent to the prefix
        # so accessing the 5-char code is easier post-chop)
        chop = p.split(prefixes[shp])

        # If it had the prefix (i.e. if we care about it), length
        # of output list will be > 1
        if len(chop) > 1:

            # Get the key code; it's the first 5 chars in the 2nd list element
            key_code = chop[1][:5]

            # Little more fancy footwork required here, since shapefiles
            # are basically @sshole files with like 6 components, 
            # ALL OF WHICH WILL HAVE THE SAME 5-CHAR CODE. Dict keys must be unique tho,
            # So the value of the dict MUST BE A LIST containing all the filepaths
            # associated with a given 5-char code. So then, if the code isn't in the dict,
            # add it and add the first filepath as single element in a list
            if not key_code in shp_filepaths:
                shp_filepaths[key_code] = [p]

            # For all subsequent matching shapefile components (i.e. where the key
            # is already in the dictionary), simply append the filepath to the list at that key
            else:
                shp_filepaths[key_code].append(p)

    return shp_filepaths



########## ########## ########## 

# At this point we have two dicts of filepaths:
# one for mdb files and one for shp files.
# Here we smash them both together in one BIG dict
# (a dict of dicts technically); then just print some 
# outputs to ensure our dict is what we think it is
def assemble_filepaths(mdb_filepaths, shp_filepaths):

    # One-liner assembling the dict of dicts
    filepaths = {mdb: mdb_filepaths, shp: shp_filepaths}

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

# This function rounds up a list of field offices (satellites).
# For testing, the field office names are simply derived from 
# listdir at the root of our test data. In reality, they will supposedly
# come from an attribute field in a feature service
def get_satellites(satellite_table):

    # The field in the table containing the names of all the field offices
    # This is currently a real field name but in a dummy/testing table
    search_field = "FieldOffices"

    # Just get all the values of this field for all the rows in the table
    satellite_list = [row[0] for row in arcpy.da.SearchCursor(satellite_table, search_field)]

    # We are copying FROM mothership so exclude her
    # from the list of copy TO hosts
    # NOTE: In order to test getting data from an ArcGIS Service table
    # but still without access to UNC dir for testing, I'm hard-coding
    # the real-deal OR mothership server name here for now. Long story.
    # I swear there is a method to the madness. In the final version this
    # would not be hard-coded but would just be the "mothership" var
    if "aioorpo23fp1" in satellite_list:
        satellite_list.remove("aioorpo23fp1")

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

                    # Try the copy thing
                    try:
                        shutil.copy(path, satellite_dirs[ext])

                    # If it didn't work, deal with that it didn't work
                    # (I will expand/fix this block I swear)
                    except Exception as e:
                        print(e)



########## ########## ########## ########## ########## ########## 

# DO THE THING
# I.E. ALL THE CALLS

mothership_dirs = get_mothership_dirs()

consolidate_mdbs(mothership_dirs)

mdb_filepaths = get_mdb_filepaths(mothership_dirs[mdb])

shp_filepaths = get_shp_filepaths(mothership_dirs[shp])

mothership_filepaths = assemble_filepaths(mdb_filepaths, shp_filepaths)

satellite_list = get_satellites(satellite_table)

iter_satellites(mothership_filepaths, satellite_list)

