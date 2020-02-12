#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Nov 26 2019
@author: changyuchang
"""

"""
Python functions for simulation in self-assembly, monoculture, and pairwise competition. 
"""

import numpy as np
import scipy as sp
import pandas as pd
import matplotlib.pyplot as plt
from community_simulator import *
from community_simulator.usertools import *
from community_simulator.visualization import *

# Import the algorithms
from community_selection.B_community_phenotypes import *
from community_selection.C_selection_algorithms import *
from community_selection.D_migration_algorithms import *


# Functions for experimental setup
def make_regional_pool(assumptions):
    """
    Create a regional species pool that has each species' relative abundance
    
    assumptions = dictionary of metaparameters from community-simulator

    """
    # Total number of species (specialist + generalist)
    S_tot = int(np.sum(assumptions['SA']) + assumptions['Sgen']) 

    # Assign drawn values based on power-law distribution
    pool = np.random.power(1, size  = S_tot)
    
    # Relative species abundance in regional pool
    pool = pool/np.sum(pool)
    
    return pool
    

def draw_species_function(assumptions):
    """
    Draw species-specific functions
    
    assumptions = dictionary of metaparameters from community-simulator
    
    Return:
    function_species, function_interaction
    """
    # Total number of species in the pool
    S_tot = int(np.sum(assumptions['SA']) + assumptions['Sgen']) 
    
    # Species-specific function, 1-D array
    function_species = np.random.normal(0, assumptions["sigma"], size = S_tot)
    
    # Interaction-specific function, 2-D n by n array
    function_interaction = np.array(np.random.normal(0, assumptions["sigma"] * assumptions["alpha"], size = S_tot * S_tot)).reshape(S_tot, S_tot)

    return function_species, function_interaction


def prepare_experiment(assumptions, seed = 1):
    """
    Prepare the experimental setting shared by all assembly experiments
    
    assumptions = dictionary of metaparameters from community-simulator
    
    Return:
    species_pool
    """
    np.random.seed(seed) 
    
    # Make parameters
    params = MakeParams(assumptions) 
    
    # Generate a species pool with the species abundance
    species_pool = make_regional_pool(assumptions) 
    
    # Generate species function
    function_species, function_interaction = draw_species_function(assumptions)
    
    return params, species_pool, function_species, function_interaction

def sample_from_pool(plate_N, scale = 10**6, inocula = 10**6, initial_inocula_pool = True):
    """
    Sample communities from regional species pool.
    In order to create variability in the pool, split the species pool into two pools, one for initial inocula and one migration.
    For initial inocula, use the even number species, whereas for initla pool, use odds number species.

    plate_N = consumer data frame
    pool = 1-D array that defines the species relative abundances in the pool
    """
    # Total number of species in this universe
    S_tot = plate_N.shape[0] 
    S_half = int(np.round(S_tot/2))
    
    # Make empty plate
    N0 = np.zeros((plate_N.shape)) # Make empty plate
    
    # Consumer index
    consumer_index = plate_N.index 
    
    # Well index
    well_names = plate_N.columns

    # Sample initial community for each well; the part is from Jean's code
    if initial_inocula_pool == True:
        for k in range(plate_N.shape[1]):
            # For each well, sample community from different microbiome sample
            np.random.seed(k + 1) 
            pool = np.random.power(1, size  = S_half) # Power-law distribution
    #        pool = pool * np.random.binomial(1, 0.5, size = S_tot) # Add additional varaibility here by randomly choosing half of the species and set the probabilities of drawing them to 0 
            pool = pool/np.sum(pool) # Normalize the pool
            consumer_list = np.random.choice(np.array(range(0, S_tot, 2)), size = inocula, replace = True, p = pool) # Draw from the pool
            my_tab = pd.crosstab(index = consumer_list, columns = "count") # Calculate the cell count
            N0[my_tab.index.values,k] = np.ravel(my_tab.values / scale) # Scale to biomass
    elif initial_inocula_pool == False:
        for k in range(plate_N.shape[1]):
            np.random.seed(k + 1) 
            pool = np.random.power(1, size  = S_half) # Power-law distribution
            pool = pool/np.sum(pool) # Normalize the pool
            consumer_list = np.random.choice(np.array(range(1, S_tot, 2)), size = inocula, replace = True, p = pool) # Draw from the pool
            my_tab = pd.crosstab(index = consumer_list, columns = "count") # Calculate the cell count
            N0[my_tab.index.values,k] = np.ravel(my_tab.values / scale) # Scale to biomass


    # Make data.frame
    N0 = pd.DataFrame(N0, index = consumer_index, columns = well_names)

    return N0


# Make initial state
## Make monos
def make_synthetic_mono(assumptions):
    """
    Make the synthetic monoculture with all community in the pool
    
    assumptions = dictionary of metaparameters
    
    Return:
    N0 = initial consumer populations
    """
    # Extract parameters from assumption
    S_tot = int(np.sum(assumptions['SA']) + assumptions['Sgen'])
    F = len(assumptions['SA'])
    
    # Construct lists of names of resources, consumers, resource types, consumer families and wells
    family_names = ['F'+str(k) for k in range(F)]
    consumer_names = ['S'+str(k) for k in range(S_tot)]
    consumer_index = [[family_names[m] for m in range(F) for k in range(assumptions['SA'][m])]
                      +['GEN' for k in range(assumptions['Sgen'])],consumer_names]
    well_names = ['W'+str(k) for k in range(S_tot)]
    
    # Make data.frame for community-simulator input
    N0 = np.eye(S_tot)
    N0 = pd.DataFrame(N0, index = consumer_index, columns = well_names)

    return N0

## Make synthetic community with given ratios
def make_synthetic_community(assumptions, species_list, number_species = 2, initial_frequency = [[0.5, 0.5], [0.95, 0.05]]):
    """
    Make synthetic community inocula of all pairwise combination
    
    species_list = consumer ID that will be mixed 
    assumptions = dictionary of metaparameters
    number_species = number of species in a community. Set to 2 for pairs, 3 for trios, etc
    initial_frequency = list of pair frequencies

    Return: N0 = initial consumer populations
    """
    # Stopifnot
    #assert max(species_list) <= len(species_pool), "Some species in the list are not in the pool."
    assert len(species_list) >= number_species, "Cannot make pair from one species."
    assert any(list((sum(x) == 1 for x in initial_frequency))), "Sum of initial frequencies is not equal to 1."
    assert any(list((len(x) == number_species for x in initial_frequency))), "Length of initial frequencies is not equal to number of species."
    

    # All possible combinations of species for given number of species added to a well
    from itertools import combinations
    consumer_pairs = list(combinations(species_list, number_species))
    
    # Extract parameters from assumption
    S_tot = int(np.sum(assumptions['SA'])+assumptions['Sgen'])
    F = len(assumptions['SA'])
    
    # Construct lists of names of resources, consumers, resource types, consumer families and wells
    family_names = ['F'+str(k) for k in range(F)]
    consumer_names = ['S'+str(k) for k in range(S_tot)]
    consumer_index = [[family_names[m] for m in range(F) for k in range(assumptions['SA'][m])]
                      +['GEN' for k in range(assumptions['Sgen'])],consumer_names]
    well_names = ['W'+str(k) for k in range(len(consumer_pairs) * len(initial_frequency))]
    

    # Create empty plate
    N0 = np.zeros(shape = [S_tot, len(consumer_pairs) * len(initial_frequency)])
    
    # Fill the plate with species pairs
    for k in range(len(initial_frequency)):
        for i in range(len(consumer_pairs)):
            N0[consumer_pairs[i], k * len(consumer_pairs) + i] = 1 * initial_frequency[k]

    # Make data.frame for community-simulator input
    N0 = pd.DataFrame(N0, index = consumer_index, columns = well_names)

    return N0

## Make initial state. Function added from Bobby's code 
def make_initial_state(assumptions, N0):
    """
    Construct initial state, at unperturbed resource fixed point.
    
    assumptions = dictionary of metaparameters
        'SA' = number of species in each family
        'MA' = number of resources of each type
        'Sgen' = number of generalist species
        'n_wells' = number of independent wells in the experiment
        'S' = initial number of species per well
        'food' = index of supplied "food" resource
        'R0_food' = unperturbed fixed point for supplied food resource
    N0 = consumer populations made from make_synthetic_*()
    
    Returns:
    N0 = initial consumer populations
    R0 = initial resource concentrations
    """

    #PREPARE VARIABLES
    #Force number of species to be an array:
    if isinstance(assumptions['MA'],numbers.Number):
        assumptions['MA'] = [assumptions['MA']]
    if isinstance(assumptions['SA'],numbers.Number):
        assumptions['SA'] = [assumptions['SA']]
    #Force numbers of species to be integers:
    assumptions['MA'] = np.asarray(assumptions['MA'],dtype=int)
    assumptions['SA'] = np.asarray(assumptions['SA'],dtype=int)
    assumptions['Sgen'] = int(assumptions['Sgen'])

    #Extract total numbers of resources, consumers, resource types, and consumer families:
    M = int(np.sum(assumptions['MA']))
    T = len(assumptions['MA'])
    S_tot = int(np.sum(assumptions['SA'])+assumptions['Sgen'])
    F = len(assumptions['SA'])
    #Construct lists of names of resources, consumers, resource types, consumer families and wells:
    resource_names = ['R'+str(k) for k in range(M)]
    type_names = ['T'+str(k) for k in range(T)]
    family_names = ['F'+str(k) for k in range(F)]
    consumer_names = ['S'+str(k) for k in range(S_tot)]
    resource_index = [[type_names[m] for m in range(T) for k in range(assumptions['MA'][m])],
                      resource_names]
    consumer_index = [[family_names[m] for m in range(F) for k in range(assumptions['SA'][m])]
                      +['GEN' for k in range(assumptions['Sgen'])],consumer_names]
    well_names = ['W'+str(k) for k in range(N0.shape[1])] # Modify the number of wells in R0 by using the well number of N0

    R0 = np.zeros((M,N0.shape[1]))

    if not isinstance(assumptions['food'],int):
        assert len(assumptions['food']) == N0.shape[1], 'Length of food vector must equal n_wells.'
        food_list = assumptions['food']
    else:
        food_list = np.ones(N0.shape[1],dtype=int)*assumptions['food']

    if not isinstance(assumptions['R0_food'],int):
        assert len(assumptions['R0_food']) == N0.shape[1], 'Length of food vector must equal n_wells.'
        R0_food_list = assumptions['R0_food']
    else:
        R0_food_list = np.ones(N0.shape[1],dtype=int)*assumptions['R0_food']

    for k in range(N0.shape[1]):
        R0[food_list[k],k] = R0_food_list[k]

    R0 = pd.DataFrame(R0,index=resource_index,columns=well_names)

    return N0, R0


# Coalesce communities 
def coalesce_communities(plate_N1, plate_N2):
    """
    Coalesce two communities together with the plate layout
    
    """
    plate_N1_test = plate_N1.copy()
    plate_N2_test = plate_N1.copy()
    
    return plate_N1_test + plate_N2_test 
    

# Main function for simulating community
def simulate_community( 
    assumptions,
    params,
    dynamics,
    params_simulation,
    params_algorithm,
    file_name = "data/",
    assembly_type = "self_assembly",
    write_composition = False):
    """
    Simulate community dynamics by given experimental regimes
    
    params_simulation = dictionary of parameters for running experiment
    params_algorithm = dictionary of algorithms that determine the selection regime, migration regime, and community pheotypes of interest
    
    Return
    community_composition = concatenated, melted panda dataframe of community and resource composition in each transfer
    community_function = melted panda dataframe of community function
    """

    # Print out the algorithms
    print("\nAlgorithm: "+ params_algorithm["algorithm_name"][0])
    print("\n")
    print(params_algorithm[["transfer", "community_phenotype", "selection_algorithm", "migration_algorithm"]].to_string(index = False))

    # Set seeds
    np.random.seed(2)
    
    # Make initial state
    init_state = MakeInitialState(assumptions)

    # Make plate
    plate = Community(init_state, dynamics, params, scale = assumptions["scale"], parallel = True) 
    setattr(plate, "species_function", params_simulation["species_function"]) # Add the species function to the plate attributes
    setattr(plate, "interaction_function", params_simulation["interaction_function"])
    
    # Update the community composition by sampling from the pool
    print("\nGenerating initial plate")
    plate.N = sample_from_pool(plate.N, scale = assumptions["scale"], inocula = params_simulation["n_inoc"], initial_inocula_pool = True)
    
    # Empty list for saving data
    plate_data_list = list() # Plate composition
    community_function_list = list() # Community function

    # Save the inocula composition
    plate_data = reshape_plate_data(plate, transfer_loop_index = 0, assembly_type = assembly_type, community_function_name = params_algorithm["community_phenotype"][0]) # Initial state
    plate_data_list.append(plate_data)
    
    # Save the initial function
    community_function = globals()[params_algorithm["community_phenotype"][0]](plate, assumptions = assumptions) # Community phenotype
    richness = np.sum(plate.N >= 1/assumptions["scale"], axis = 0) # Richness
    biomass = list(np.sum(plate.N, axis = 0)) # Biomass
    function_data = reshape_function_data(community_function_name = params_algorithm["community_phenotype"][0], community_function = community_function, richness = richness, biomass = biomass, transfer_loop_index = 0, assembly_type = assembly_type)        
    community_function_list.append(function_data) # Transfer = 0 means that it's before selection regime works upon

    
    # Output the plate composition and community functions if write_composition set True
    if write_composition == True:
        plate_data.to_csv(file_name + "-" + params_algorithm["community_phenotype"][0] + "-T" + "{:02d}".format(0) + "-composition.txt", index = False)
        function_data.to_csv(file_name + "-" + params_algorithm["community_phenotype"][0] + "-T" + "{:02d}".format(0) + "-function.txt", index = False)

    print("\nStart propogation")
    # Run simulation
    for i in range(0, params_simulation["n_transfer"]):
        # Algorithms used in this transfer
        phenotype_algorithm = params_algorithm["community_phenotype"][i]
        selection_algorithm = params_algorithm["selection_algorithm"][i]
        migration_algorithm = params_algorithm["migration_algorithm"][i]

        # Print the propagation progress
        if (i % 5) == 0:
            print("Transfer " + str(i+1))

        # Propagation
        plate.Propagate(params_simulation["n_propagation"])
    
        # Append the composition to a list
        plate_data = reshape_plate_data(plate, transfer_loop_index = i + 1, assembly_type = assembly_type, community_function_name = phenotype_algorithm) # Transfer = 0 means that it's before selection regime works upon
        plate_data_list.append(plate_data)

        # Community phenotype, richness, and biomass
        community_function = globals()[phenotype_algorithm](plate, assumptions = assumptions) # Community phenotype
        richness = np.sum(plate.N >= 1/assumptions["scale"], axis = 0) # Richness
        biomass = list(np.sum(plate.N, axis = 0)) # Biomass
        function_data = reshape_function_data(community_function_name = phenotype_algorithm, community_function = community_function, richness = richness, biomass = biomass, transfer_loop_index = i + 1 , assembly_type = assembly_type)        
        community_function_list.append(function_data) # Transfer = 0 means that it's before selection regime works upon

        # Output the plate composition and community functions if write_composition set True
        if write_composition == True:
            plate_data.to_csv(file_name + "-" + phenotype_algorithm + "-T" + "{:02d}".format(i + 1) + "-composition.txt", index = False) # Transfer = 0 means that it's before selection regime works upon
            function_data.to_csv(file_name + "-" + phenotype_algorithm + "-T" + "{:02d}".format(i + 1) + "-function.txt", index = False)

        # Passage and tranfer matrix
        transfer_matrix = globals()[selection_algorithm](community_function)
        plate.Passage(transfer_matrix * params_simulation["dilution"])
        
        # Migration
        m = globals()[migration_algorithm](community_function) 
        plate.N = migrate_from_pool(plate, pool = params_simulation["pool"], migration_factor = m, scale = assumptions["scale"], inocula = params_simulation["n_inoc"])

        
    print("\nAlgorithm "+ params_algorithm["algorithm_name"][0] + " finished")

    # Concatenate data from from different transfers
    plate_data_con = pd.concat(plate_data_list)
    community_function_con = pd.concat(community_function_list)

    return plate_data_con, community_function_con


## Reshape the plate resource and consumer matrix for saving into a txt file
def reshape_plate_data(plate, transfer_loop_index, assembly_type, community_function_name):
    # Temporary function for adding variables to and melting df
    def melt_df(plate_df, data_type = "consumer"):
        # Consumers
        temp_df = pd.DataFrame(plate_df)
        total_number = temp_df.shape[0]
        
        ## Add variables
        temp_df["Type"] = np.repeat(data_type, total_number)
        temp_df["ID"] = range(total_number)
        temp_df["Transfer"] = np.repeat(str(transfer_loop_index), total_number)
        temp_df["Assembly"] = np.repeat(assembly_type, total_number)
        temp_df["CommunityPhenotypeName"] = np.repeat(community_function_name, total_number)
         
        ## Melt the df
        temp_df = pd.melt(temp_df, id_vars = ["Transfer", "CommunityPhenotypeName", "Assembly", "Type", "ID"], var_name = "Well", value_name = "Abundance")
        temp_df = temp_df[["Assembly", "CommunityPhenotypeName", "Well", "Transfer", "Type", "ID", "Abundance"]]
        temp_df = temp_df[temp_df.Abundance != 0] # Remove zero abundances
        return temp_df
        
    # Melt the df
    temp_plate = plate.copy() # Copy the original plate 
    df_N = melt_df(temp_plate.N, data_type = "consumer")
    df_R = melt_df(temp_plate.R, data_type = "resource")
    
    # Concatenate dataframes
    merged_df = pd.concat([df_N, df_R]) 
    merged_df["Index"] = list(range(0, merged_df.shape[0]))
    merged_df.set_index("Index", inplace = True)

    return merged_df # Return concatenated dataframe


def reshape_function_data(community_function_name, community_function, richness, biomass, transfer_loop_index, assembly_type):
    temp_vector1 = community_function.copy()
    temp_vector2 = richness.copy()
    temp_vector3 = biomass.copy()
    
    # Number of wells
    number_well = len(richness)
    # Make data.frame
    temp_df = pd.DataFrame({"Assembly": np.repeat(assembly_type, number_well),
    "CommunityPhenotypeName": np.repeat(community_function_name, number_well),
    "Well": ["W" + str(i) for i in range(number_well)], 
    "Transfer": np.repeat(str(transfer_loop_index), number_well), 
    "CommunityPhenotype": temp_vector1,
    "Richness": temp_vector2,
    "Biomass": temp_vector3})
    
    # Turn the transfer columns as numeric
    temp_df[["Transfer"]] = temp_df[["Transfer"]].apply(pd.to_numeric)
    
    return temp_df 

 

# Make library of algorithms
def make_algorithm_library():
    """
    Show the table of algorithms in this package
    """
    import re
    import pandas as pd
    
    # Find directory of community_selection modultes
    import community_selection
    module_dir = community_selection.__file__
    module_dir = re.sub("__init__.py", "", module_dir) 
    
    # 
    algorithm_types = ["community_phenotypes", "selection_algorithms", "migration_algorithms"]
    algorithms = list()
    
    for i in range(len(algorithm_types)):
    
        # Open files
        file_algorithm_phenotype = open(module_dir + ["B", "C", "D"][i] + "_" + algorithm_types[i] + ".py", "r")
        
        # Read lines
        line_list = list()
        line = file_algorithm_phenotype.readline()
        cnt = 1
        
        while line:
            line = file_algorithm_phenotype.readline()
            # Only count non-commented-out functions
            if line.startswith("#") == False: 
                line_list.append(line.strip())
            cnt += 1
        
        # Regular expression
        algorithm_names = re.findall("def \w+", " ".join(line_list))
        
        list_algorithm = [re.sub("^def ", "", x) for x in algorithm_names]
        
        # Write the files
        algorithms.append(pd.DataFrame({"AlgorithmType": re.sub("s$", "", algorithm_types[i]), "AlgorithmName": list_algorithm}))
     
    return pd.concat(algorithms)


# Migrate from species pool to the plate 
def migrate_from_pool(plate, pool, migration_factor, scale, inocula):
    # Migration plate
    migration_plate = sample_from_pool(plate.N, scale = scale, inocula = inocula, initial_inocula_pool = False) * migration_factor # Migration factor is a list determined by migration algorithms and community function
    
    # Migration
    plate_migrated = plate.N + migration_plate 

    return plate_migrated

# Plot community function
def plot_community_function(function_df):
    function_df.plot.scatter(x = "Transfer", y = "CommunityPhenotype")

# Plot transfer matrix
def plot_transfer_matrix(transfer_matrix):
    import seaborn as sns
    fig,ax=plt.subplots()
    sns.heatmap(transfer_matrix,ax=ax)
    ax.set_xlabel('Old well',fontsize=14)
    ax.set_ylabel('New well',fontsize=14)
    ax.set_title(r'Transfer Matrix',fontsize=14)
    plt.show()
    
    return fig
    


def make_algorithms(params_simulation):
    # Algorithms
    ## Simple screening
    simple_screening = pd.DataFrame({
        "algorithm_name": "simple_screening",
        "transfer": range(1, params_simulation["n_transfer"] + 1),
        "community_phenotype": params_simulation["selected_function"],
        "selection_algorithm": "no_selection",
        "migration_algorithm": "no_migration"
    })

    ## Direction selection
    direct_selection = pd.DataFrame({
        "algorithm_name": "direct_selection",
        "transfer": range(1, params_simulation["n_transfer"] + 1),
        "community_phenotype": params_simulation["selected_function"], 
        "selection_algorithm": ["no_selection" for i in range(9)] + ["direct_selection_select"] + ["no_selection" for i in range(params_simulation["n_transfer"] - 10)], 
        "migration_algorithm": ["no_migration" for i in range(9)] + ["direct_selection_migrate"] + ["no_migration" for i in range(params_simulation["n_transfer"] - 10)]
    })


    ## Select top 25%
    select_top25 = pd.DataFrame({
        "algorithm_name": "select_top25",
        "transfer": range(1, params_simulation["n_transfer"] + 1),
        "community_phenotype": params_simulation["selected_function"],
        "selection_algorithm": ["no_selection" for i in range(9)] + ["select_top25percent"] + ["no_selection" for i in range(params_simulation["n_transfer"] - 10)], 
        "migration_algorithm": "no_migration"
    })  

    ## Select top 10%
    select_top10 = pd.DataFrame({
        "algorithm_name": "select_top10",
        "transfer": range(1, params_simulation["n_transfer"] + 1),
        "community_phenotype": params_simulation["selected_function"],
        "selection_algorithm": ["no_selection" for i in range(9)] + ["select_top10percent"] + ["no_selection" for i in range(params_simulation["n_transfer"] - 10)], 
        "migration_algorithm": "no_migration"
    })

    ## Multiple direct selection
    multiple_direct_selection = pd.DataFrame({
        "algorithm_name": "multiple_direct_selection",
        "transfer": range(1, params_simulation["n_transfer"] + 1),
        "community_phenotype": params_simulation["selected_function"], 
        "selection_algorithm": ["no_selection" for i in range(5)] + ["direct_selection_select" for i in range(5)] + ["no_selection" for i in range(params_simulation["n_transfer"] - 10)], 
        "migration_algorithm": ["no_migration" for i in range(5)] + ["direct_selection_migrate" for i in range(5)] + ["no_migration" for i in range(params_simulation["n_transfer"] - 10)]
    })

    ## Pair top communities
    pair_top_communities = pd.DataFrame({
        "algorithm_name": "pair_top_communities",
        "transfer": range(1, params_simulation["n_transfer"] + 1),
        "community_phenotype": params_simulation["selected_function"],
        "selection_algorithm": ["no_selection" for i in range(9)] + ["pair_top"] + ["no_selection" for i in range(params_simulation["n_transfer"] - 10)], 
        "migration_algorithm": "no_migration"
    })

    ## Swenson2000
    swenson2000 = pd.DataFrame({
        "algorithm_name": "swenson2000",
        "transfer": range(1, params_simulation["n_transfer"] + 1),
        "community_phenotype": params_simulation["selected_function"],
        "selection_algorithm": ["select_top25percent" for i in range(10)] + ["no_selection" for i in range(params_simulation["n_transfer"] - 10)], 
        "migration_algorithm": "no_migration"
    })


    # Save the algorithms
    algorithms = pd.concat([simple_screening, direct_selection, select_top25, select_top10, 
                            multiple_direct_selection, pair_top_communities, swenson2000])
    
    return algorithms












