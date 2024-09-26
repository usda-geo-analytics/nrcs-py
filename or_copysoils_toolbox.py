import os
from pathlib import Path
import datetime
import shutil
import sys
import arcpy



########## ########## ########## ########## ########## ########## 
# TOOL FUNCTIONS

# For anything we want to print, just call this function
# to add both an arcpy message and write it to the log file
def print_n_log(message):

    arcpy.AddMessage(message)
    log_file.write(message)



########## ########## ########## 

# Open our log file and add a heading with date/time stamp
# This will virtually ALWAYS create a new file (not overwrite)
# because the datetime stamp in the filename includes hour|minute|second
def open_log(log_dir):

    # Check if the parameter exists; if it doesn't; make it:
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Check to make sure they supplied a dir not a file;
    # If they supplied a filepath, scold them:
    if not os.path.isdir(log_dir):
        arcpy.AddMessage("""\nWarning! The log directory supplied is not a valid directory.
                         \n(Did you specify a full file path?)
                         \nA new log file will be generated in the filepath's directory.\n""")
        
        # If they supplied a filepath, use the dir the file is in
        # to make the new log file; no hard feelings
        if os.path.isfile(log_dir):
            new_dir = os.path.dirname(log_dir)
            log_dir = new_dir

    # Still wrap in try, because the answer to "What could go wrong??" IS NEVER "nothing"
    try:
        log_file = open(Path(log_dir, f"OR_CopySoils_Log{datetime_stamp}.txt"), "a")
        log_file.write(f"""\nHEREIN BEGINS THE LOGGING FOR THE OREGON COPY SOILS SCRIPT
                       (Date / Time: {datetime_stamp})\n""")

    # Print our message and the exception using arcpy
    except Exception as e:
        arcpy.AddMessage("""
                         \nThere was an error opening the log file;
                         \nplease confirm the log directory you supplied is correct and accessible!
                         \nScript will exit.\n""")
        arcpy.AddMessage(f"\n{e}\n")
        sys.exit()
    
    return log_file



########## ########## ########## 

# "Path" only works with full "\\host\share" path and "data" is the share
def get_mothership():

    # Testing switch uses letter drives vice UNC paths (because I don't
    # have access to the collection of hosts this would actually be run against)
    if test_local:
        # For testing "mothership" is just the name of a dir
        mothership = "_F"

    # Unfortunately I don't have a way to test this funcitonality yet
    else:
        # Outside of testing, "mothership" is the host of a \\host\share UNC
        mothership = "aioorpo23fp1"

    return mothership



########## ########## ########## 

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
    #print("\nOutput of get_mothership_dirs() (var mothership_dirs):")
    #for k, v in mothership_dirs.items():
        #print(f"\tKey: {k}, value: {v}")

    print_n_log(f"\nSuccessfully retrieved MDB and SHP directories for state office '{mothership}'\n")

    return mothership_dirs



########## ########## ########## 

# Walk the dir where all the mdbs are scattered among various subfolders
# and consolidate them into one "flat" dir
def consolidate_mdbs():

    # Make the new consolidated FY dir if it does not already exist
    try:
        os.makedirs(mothership_dirs[mdb], exist_ok= True)
    except Exception as e:
        print_n_log(f"\n{e}\n")

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
                    print_n_log(f"\n\tSUCCESS: The file:\n\t{from_path} \n\t...was successfully copied to:\n\t{to_path}\n")

                # If it didn't work, deal with that it didn't work
                # (I will expand/fix this block I swear)
                except Exception as e:
                    print_n_log(f"\n\tERROR: The attempt to copy the file:\n\t{from_path} \n\t...to:\n\t{to_path}\n\t...resulted in the following error:\n")
                    print_n_log(f"\n\t{e}\n")

    print_n_log("\nSuccessfully consolidated state office MDB files\n")



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

    print_n_log("\nSuccessfully retrieved state office MDB filepaths\n")

    return mdb_filepaths



########## ########## ########## 

# Hahaha just because I don't have to flatten the shp dir
# DOES NOT MEAN IT'S ALREADY FLAT. It's not. Joke's on me.
# But not a big deal; I just don't get to use the one-liner.
# Instead this handy function just roots through the mothership soils dir
# and grabs the files from the subdirs, which are only 1 level deep
def get_pre_prepaths(shp_dir):

    # List to hold the actual filepaths
    pre_prepaths = []

    # List comprehension to get everything I care about within soils dir
    pre_subdirs = [str(Path(shp_dir, f)) for f in os.listdir(shp_dir) if f.startswith("soil_")]

    # Just kidding I have to make sure the things I care about are actually dirs
    soil_subdirs = [f for f in pre_subdirs if os.path.isdir(f)]

    # Now just iter through those dirs...
    for dir in soil_subdirs:

        # ...get all the full paths I care about...
        sub_paths = [str(Path(dir, f)) for f in os.listdir(dir) if f.startswith(prefixes[shp])]

        # ...and ongoingly smash them into our list
        pre_prepaths.extend(sub_paths)

    print_n_log("\nSuccessfully assembled SHP prepaths\n")

    return pre_prepaths



########## ########## ########## 

# This function applies datestamps to shapefiles,
# First by building the appropriate strings
# then actually renaming the files
def apply_datestamps(pre_prepaths):

    # Empty list to hold pre-filepaths
    prepaths = []

    # Iterate PRE-pre-paths (which are the preexisting files)
    for p in pre_prepaths:

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
            try:
                os.replace(p, dated)
            except Exception as e:
                print_n_log(f"\n{e}\n")

        # Otherwise if the file's already stamped, carry on
        else:
            dated = p

        # Add the datestamped file path string to our list
        prepaths.append(dated)

    print_n_log("\nSuccessfully applied datestamps to SHPs\n")

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
    pre_prepaths = get_pre_prepaths(shp_dir)

    # Do the apply_datestamps boogie
    prepaths = apply_datestamps(pre_prepaths)

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

    print_n_log("\nSuccessfully retrieved state office SHP filepaths\n")

    return shp_filepaths



########## ########## ########## 

# At this point we have two dicts of filepaths:
# one for mdb files and one for shp files.
# Here we smash them both together in one BIG dict
# (a dict of dicts technically); then just print some 
# outputs to ensure our dict is what we think it is
def assemble_filepaths():

    # One-liner assembling the dict of dicts
    filepaths = {mdb: mdb_filepaths, shp: shp_filepaths}

    # Print All The Things to make sure our output is what we expect
    #print(f"\nOutput of get_filepaths (var filepaths):")
    #for k, val in filepaths.items():
        #print(f"\tKey: {k}, Values:")
        #for x, y in val.items():
            #print(f"\t\tSubkey: {x}, Values:")
            #for x in y:
                #print(f"\t\t\t{x}")
                  
    print_n_log("\nSuccessfully assembled ALL filepaths\n")

    return filepaths


########## ########## ########## 

# This function rounds up a list of field offices (satellites).
# For testing, the field office names are simply derived from 
# listdir at the root of our test data. In reality, they will supposedly
# come from an attribute field in a feature service
def get_satellites():

    # The field in the table containing the names of all the field offices
    # This is currently a real field name but in a dummy/testing table
    search_field = "FieldOffices"

    # Just get all the values of this field for all the rows in the table
    try:
        satellite_list = [row[0] for row in arcpy.da.SearchCursor(satellite_table, search_field)]
    except Exception as e:
        print_n_log(f"\n{e}\n")

    # We are copying FROM mothership so exclude her
    # from the list of copy TO hosts
    # NOTE: In order to test getting data from an ArcGIS Service table
    # but still without access to UNC dir for testing, I'm hard-coding
    # the real-deal OR mothership server name here for now. Long story.
    # I swear there is a method to the madness. In the non-test version this
    # would not be hard-coded but would just be the "mothership" var
    if "aioorpo23fp1" in satellite_list:
        satellite_list.remove("aioorpo23fp1")

    # Print All The Things to make sure our output is what we expect
    #print("\nOutput of get_satellites (satellite_list):")
    #for s in satellite_list:
        #print(f"\t{s}")

    print_n_log("\nSuccessfully retrieved field office server names\n")

    return satellite_list



########## ########## ########## 

# This is called once for every satellite within the list of
# satellite field offices (i.e. not the main office)
# It constructs a dictionary of extension: directory key/value pairs
# In the same manner as we did for mothership;
# made it a different function though since full dirs differ slightly
def get_satellite_dirs(satellite):

    # For this satellite, full path to where mdbs reside
    mdb_dir = Path(get_root(satellite), "FOTG", "Section_II")

    # For this satellite, path to full path to where shps reside
    shp_dir = Path(get_root(satellite), "geodata", "soils")

    # Put it together and what've you got, bippity boppity boo
    satellite_dirs = {mdb: mdb_dir, shp: shp_dir}

    # Print All The Things to make sure our output is what we expect
    #print(f"\nOutput of get_satellite_dirs({satellite}):")
    #for k, v in satellite_dirs.items():
        #print(f"\tKey: {k}, value: {v}")

    print_n_log(f"\nSuccessfully retrieved MDB and SHP directories for field office '{satellite}'\n")

    return satellite_dirs



########## ########## ########## 

# For each satellite office, we must figure out what files,
# of all possible files that we could copy there, are actually needed
# We do this by looking at what files are already in these dirs
# Specifically we look at the 5-char codes within the filenames in these dirs
# This function is called once for each satellite field office,
# returns a dict (keys: mdb, shp) of 5-char codes representing the files we need
def get_sat_required(satellite_dirs, sat):

    # Initialize empty dict
    sat_required = {}

    # Iterate through both mdb and shp dirs for the given satellite
    for k, v in satellite_dirs.items():

        # Create a list of all files of the required type within this dir
        current_files = [f for f in os.listdir(v) if f.endswith(k)]

        # Create a new list by filtering the above list; we only want files
        # that include our specified prefix
        filtered_list = [f for f in current_files if f.startswith(prefixes[k])]

        # A little fancy footwork to chop up the file path, get the 5-char code,
        # stuff it in a list, then cast to set because I don't need or want dups;
        # finally stuff the set as value in dict w/extension as key for easy reference
        sat_required[k] = set([str(f.split(prefixes[k])[1][:5]) for f in filtered_list])
        
    # Print All The Things to make sure our output is what we expect
    #print(f"\nOutput of get_sat_required {sat}:")
    #for k, v in sat_required.items():
        #print(f"\tKey: {k}, value: {v}")

    print_n_log(f"\nSuccessfully retrieved required 5-char codes for field office '{sat}'\n")

    return sat_required



########## ########## ########## 

# Current functionality here is to delete any preexisting 
# archive folders & contents, re-create archive folder, then shunt
# everything currently in the main dir into the archive dir.
# Currently we are NOT deleeting anything in the archive dir
# at the end of the script, for just-in-case incidents
def archive_old(satellite_dirs, ext):
    
    # Construct the path to the "Old to delete" dir
    # This is a subfolder within the dir
    # to which we want to copy the new files
    archive = Path(satellite_dirs[ext], "Old to Delete")

    # If it exists (as it should), delete it and all files in it
    if os.path.exists(archive):
        try:
            shutil.rmtree(archive)
        except Exception as e:
            print_n_log(f"\n{e}\n")

    # Then remake it so it's a fresh folder w/no files in it
    try:
        os.makedirs(archive, exist_ok=True)
    except Exception as e:
        print_n_log(f"\n{e}\n")

    # Get all the files in the current directory
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

    print_n_log(f"\nSuccessfully archived preexisting files\n")



########## ########## ########## 

# Iterate through the list of all field office servers
# (that are not the mothership/state office server)
# For each office, get the directories where the mdbs and shps go,
# look through all the files currently in those dirs,
# get a set of the 5-digit codes for those files
# which are ostensibly the files that this field office needs),
# archive all the current files to a subdir we (re)create,
# then use our lookup dict to copy the fresh 
# appropriate/required files to the current dir
def iter_satellites():

    for sat in satellite_list:

        # Call to the function to get the pair of dirs for mdbs and shps
        satellite_dirs = get_satellite_dirs(sat)

        # Call to the function to get the 5-char codes for the files
        # already in both those dirs
        sat_required = get_sat_required(satellite_dirs, sat)

        # Iter through the dict containing the 5-char codes
        for ext, code_set in sat_required.items():

            # Call to function to archive files currently this dir
            archive_old(satellite_dirs, ext)

            # For each 5-char code:
            for code in code_set:

                # Here we begin iterating through the master list of
                # all possible files that could be copied--or rather,
                # we look at the master files FOR THE CURRENT extension,
                # for the current 5-char code, and copy only those
                # to the current satellite dir
                for path in mothership_filepaths[ext][code]:

                    # Try the copy thing
                    try:
                        shutil.copy(path, satellite_dirs[ext])
                        print_n_log(f"\n\tSUCCESS: The file:\n\t{path} \n\t...was successfully copied to:\n\t{satellite_dirs[ext]}\n")

                    # If it didn't work, deal with that it didn't work
                    except Exception as e:
                        print_n_log(f"\n\tERROR: The attempt to copy the file:\n\t{path} \n\t...to:\n\t{satellite_dirs[ext]} \n\t...resulted in the following error:\n")
                        print_n_log(f"\n\t{e}\n")
    
    print_n_log(f"\nSuccessfully iterated all field office directories\n")



if __name__ == "__main__":

    ########## ########## ########## ########## ########## ########## 
    # INPUT PARAMETERS
    # These could be exposed in e.g. python toolbox

    # Switch to control whether this is run on UNCs or letter dr
    # (Construction of path for each is slightly different)
    test_local = arcpy.GetParameterAsText(0)

    # This dir is only ever referenced for testing
    test_dir = arcpy.GetParameterAsText(1)

    # Built in a means to test retrieval of all field office host names from table service
    # Just replace this URL with URL to table service (including layer index!)
    satellite_table = arcpy.GetParameterAsText(2)
    # satellite_table = r"https://services.arcgis.com/LLVEmB8Lsae3Um4s/arcgis/rest/services/NRCS_CopySoils_FieldOffices/FeatureServer/0"

    # FY stamp to append to MDBs
    # Now that this is a parameter I should do at least a little validation on it...
    fy = arcpy.GetParameterAsText(3)
    fy_stamp = f"_FY{fy}"

    # Directory where log file should be created
    log_dir = arcpy.GetParameterAsText(4)



    ########## ########## ########## ########## ########## ########## 
    # NON-INPUT PARAMETERS

    # Provides datestamp string in the format of "_YYYYMM", ready to append
    date_stamp = datetime.datetime.now().strftime("_%Y%m")

    # Provides datestamp string in the format of "_YYYYMMDD-HHMMSS", more fine-grain for logging
    datetime_stamp = datetime.datetime.now().strftime("_%Y%m%d-%I%M%S%p")

    # To avoid hard-coded strings everywhere
    mdb = ".mdb"
    shp = ".shp"

    # Non-hard-coded way to refer to appropriate filename prefixes where appropriate
    prefixes = {mdb: "soil_d_", shp: "soilmu_a_"}



    ########## ########## ########## ########## ########## ########## 
    # DO THE THING
    # I.E. ALL THE CALLS

    log_file = open_log(log_dir)

    mothership = get_mothership()

    mothership_dirs = get_mothership_dirs()

    consolidate_mdbs()

    mdb_filepaths = get_mdb_filepaths(mothership_dirs[mdb])

    shp_filepaths = get_shp_filepaths(mothership_dirs[shp])

    mothership_filepaths = assemble_filepaths()

    satellite_list = get_satellites()

    iter_satellites()

    print_n_log(f"\nScript completed successfully\n")
    
    log_file.close()

