#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mar 09 2020
@author: changyuchang
"""
import numpy as np
import scipy as sp
import pandas as pd
from community_simulator import *
from community_simulator.usertools import *
from community_selection.A_experiment_functions import *
from community_selection.E_protocols import *

def sample_from_pool(plate_N, assumptions,n=None):
    """
    Sample communities from regional species pool.
    In order to create variability in the pool, split the species pool into two pools, one for initial inocula and one migration.
    For initial inocula, use the even number species, whereas for initla pool, use odds number species.

    plate_N = consumer data.frame
    pool = 1-D array that defines the species relative abundances in the pool
    """
    S_tot = plate_N.shape[0] # Total number of species in the pool
    N0 = np.zeros((plate_N.shape)) # Make empty plate
    consumer_index = plate_N.index
    well_names = plate_N.columns
    if n is None:
        n = assumptions['n_inoc'] #if not specified n is n_inoc
    # Draw community
    if assumptions['monoculture'] == False:
        # Sample initial community for each well
        for k in range(plate_N.shape[1]):
            pool = np.random.power(0.01, size = S_tot) # Power-law distribution
            pool = pool/np.sum(pool) # Normalize the pool
            consumer_list = np.random.choice(S_tot, size = n , replace = True, p = pool) # Draw from the pool
            my_tab = pd.crosstab(index = consumer_list, columns = "count") # Calculate the cell count
            N0[my_tab.index.values,k] = np.ravel(my_tab.values / assumptions['scale']) # Scale to biomass

        # Make data.frame
        N0 = pd.DataFrame(N0, index = consumer_index, columns = well_names)

    # Monoculture plate
    elif assumptions['monoculture'] == True:
        N0 = np.eye(plate_N.shape[0]) *assumptions['n_inoc']/assumptions['scale']
        N0 = pd.DataFrame(N0, index = consumer_index, columns = ["W" + str(i) for i in range(plate_N.shape[0])])


    return N0

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

def make_assumptions(input_file,row):
	'''  Generate the assumptions dictionary from input file and row of input file '''
	#Load row dat and default assumptions
	row_dat = pd.read_csv(input_file, keep_default_na=False).iloc[row]
	assumptions = a_default.copy()
	original_params = MakeParams(assumptions.copy())
	#Update assumptions based on row_dat
	for k in row_dat.keys():
		#if NA default to original value 
		if k in assumptions.keys() and row_dat[k] != 'NA' :
			assumptions.update({k :row_dat[k]})
		elif k in assumptions.keys() and row_dat[k] == 'NA' :
			continue
		#some params for who we wan't to resort to there default value are not stored in assumptions but are generated by MakeParams
		elif k not in assumptions.keys() and k in original_params.keys() and row_dat[k] != 'NA':
			assumptions.update({k :row_dat[k]})
		elif k not in assumptions.keys() and k  in original_params.keys() and row_dat[k] == 'NA':
			assumptions.update({k:original_params[k]})
		else:
			if row_dat[k] != 'NA':
				assumptions.update({k :row_dat[k]})
			else:
				assumptions.update({k :np.nan})
				
	#These two assumptions are generated from combinations of other paramaters
	assumptions.update({'SA' :row_dat['sn']*np.ones(row_dat['sf'])  }) #Number of consumers in each Specialist family
	assumptions.update({'MA' :row_dat['rn']*np.ones(row_dat['rf'])  }) #Number of resources in each class
	
	#MakeParams does not work with numpy type for R0_food so convert to base python if not using default
	if not isinstance(assumptions['R0_food'],int):
		assumptions['R0_food'] = assumptions['R0_food'].item()
	
	#When running monoculture (every isolate in monoculture)
	if assumptions['monoculture'] :
		assumptions.update({"n_wells": int(np.sum(assumptions["SA"])  + assumptions["Sgen"])})
		
	#If knock_in isolate is True and no threshold is set threshold size defaults to 0
	if assumptions['bottleneck']:
		if  pd.isnull(assumptions['bottleneck_size']):
			assumptions['bottleneck_size'] =assumptions['dilution']
		else:
			assumptions['bottleneck_size'] = float(assumptions['bottleneck_size'])

	#If knock_in isolate is True and no threshold is set threshold size defaults to 0
	if assumptions['knock_in']:
		if pd.isnull(assumptions['knock_in_threshold']) :
			assumptions['knock_in_threshold'] =0
		else:
			assumptions['knock_in_threshold'] = float(assumptions['knock_in_threshold'])
		
	#If coalescence is True and no frac coalescence is set defaults to 50-50
	if assumptions['coalescence']:
		if pd.isnull(assumptions['frac_coalescence']):
			assumptions['frac_coalescence'] =0.5	
		else:
			assumptions['frac_coalescence'] = float(assumptions['frac_coalescence'])
	
	#If migration is True and no n_migration_ds is set defaults to n_inoc
	if assumptions['migration']: 
		if pd.isnull(assumptions['n_migration_ds']):
			assumptions['n_migration_ds'] =assumptions['n_inoc']
		else:
			assumptions['n_migration_ds'] = int(assumptions['n_migration_ds'])
			
		if pd.isnull(assumptions['s_migration']):
			pass
		else:
			assumptions['s_migration'] = int(assumptions['s_migration'])
			
	#If coalescence is True and no frac coalescence is set defaults to 50-50
	if assumptions['resource_shift']:
		if pd.isnull(assumptions['r_percent']):
			assumptions['r_percent'] =0.1
		else:
			assumptions['r_percent'] = float(assumptions['r_percent'])
	return assumptions
	
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
    function_interaction = np.random.normal(0, assumptions["sigma"] * assumptions["alpha"], size = S_tot * S_tot).reshape(S_tot, S_tot)
    function_interaction_p25 = np.random.binomial(1, 0.25, S_tot**2).reshape(S_tot, S_tot) * np.array(np.random.normal(0, assumptions["sigma"] * assumptions["alpha"], size = S_tot * S_tot)).reshape(S_tot, S_tot)
    
    ## Remove diagonals in the interation matrix
    np.fill_diagonal(function_interaction, 0)
    np.fill_diagonal(function_interaction_p25, 0)

    return function_species, function_interaction, function_interaction_p25

def draw_species_cost(per_capita_function, assumptions):
    """
    Draw species-specific function cost
    k_i is a conversion factor that specifies cost per function 
    """
    
    if assumptions["cost_mean"] !=0:
        cost_var = assumptions["cost_sd"]**2
        cost_k = assumptions["cost_mean"]**2/cost_var
        cost_theta = cost_var/assumptions["cost_mean"]
        cost = np.random.gamma(shape = cost_k, scale = cost_theta, size = len(per_capita_function))
        g0 = assumptions["g0"]
        gi = g0/(1-per_capita_function*cost)
    else: 
        gi = np.repeat(assumptions["g0"], len(per_capita_function))
    
    return gi

def make_medium(plate_R,assumptions):
    """
    Design medium for the plate
    if assumptions['rich_medium'] == True, make rich medium
    """
    if assumptions['rich_medium'] == True:
        np.random.seed(1)
    
		# Total number of resource in this universe
        R_tot = plate_R.shape[0] 
    
		# Make empty plate
        R0 = np.zeros((plate_R.shape)) # Make empty plate
    
		# Resource index
        resource_index = plate_R.index 
    
		# Well index
        well_names = plate_R.columns
    
        resource_pool = np.random.uniform(0, 1, size = R_tot) # Uniform distribution
        resource_pool = resource_pool/np.sum(resource_pool)
        resource_list = np.random.choice(R_tot, size = assumptions["R0_food"], replace = True, p = resource_pool) # Draw from the pool
        my_tab = pd.crosstab(index = resource_list, columns = "count")
        food_compostion = np.ravel(my_tab.values)
        for i in range(plate_R.shape[1]):
            R0[my_tab.index.values,i] = food_compostion
        R0 = pd.DataFrame(R0, index = resource_index, columns = well_names)
    else:
        R0 = plate_R
    return R0

def make_plate(assumptions,params):
    """
    prepares the plate
    """
    
    # Make dynamical equations
    def dNdt(N,R,params):
        return MakeConsumerDynamics(assumptions)(N,R,params)
    def dRdt(N,R,params):
        return MakeResourceDynamics(assumptions)(N,R,params)
    dynamics = [dNdt,dRdt]
    
    # Make initial state
    init_state = MakeInitialState(assumptions)
    
    plate = Community(init_state, dynamics, params, scale = assumptions["scale"], parallel = False) 
    
    # Add media to plate (overrides community simulator)
    plate.R = make_medium(plate.R, assumptions)
    plate.R0 = make_medium(plate.R0, assumptions)  
	   
	# Add cells to plate (overrides community simulator)
    plate.N = sample_from_pool(plate.N, assumptions)
    
    return plate
	
def add_community_function(plate, assumptions, params):
    """
    Add the function attribute to the community
    
    For f1 and f3, add species_function 
    For f2 and f4, add interaction_function
    For f5, add invasion_plate_t0 and invasion_plate_t1
    For f6, f7, and f8, add resident_plate_t0_N, resident_plate_t1_N, resident_plate_t0_R, and resident_plate_t1_R
    
    if isolates calculate function for every isolate in monoculture.
    """
    
    #Generate per capita species function
    np.random.seed(assumptions['seed']) 
    function_species, function_interaction, function_interaction_p25 = draw_species_function(assumptions)
    
    # Species function, f1 and f3
    setattr(plate, "species_function", function_species) # Species function for additive community function

    # Interactive functions, f2 , f2b and f4
    setattr(plate, "interaction_function",function_interaction) # Interactive function for interactive community function
    setattr(plate, "interaction_function_p25", function_interaction_p25)


    # Invasion function f5 or knock_in with a threshold requires us to grow isolates in monoculture to obtain their abundance.
    if (assumptions["selected_function"] == 'f5_invader_growth') | (assumptions['knock_in']):
        print("\nStabilizing monoculture plate")
        # Keep the initial plate R0 for function f7 
        setattr(plate, "R0_initial", plate.R0)
        
        assumptions_invasion = assumptions.copy()
        params_invasion = params.copy()
        
		#Update assumptions
        assumptions_invasion.update({"n_wells": np.sum(assumptions["SA"])  + assumptions["Sgen"]})
        assumptions_invasion.update({"monoculture":True})

        # Make plates
        plate_invasion = make_plate(assumptions_invasion,params_invasion)
        
		# Species function, f1 and f3 (to calculate function at end)
        setattr(plate_invasion, "species_function", function_species) # Species function for additive community function

		# Interactive functions, f2 , f2b and f4
        setattr(plate_invasion, "interaction_function",function_interaction) # Interactive function for interactive community function
        setattr(plate_invasion, "interaction_function_p25", function_interaction_p25)   
		
        
        # Grow the invader plate  to equilibrium
        for i in range(assumptions_invasion["n_transfer"] - assumptions_invasion["n_transfer_selection"]):
            plate_invasion.Propagate(assumptions_invasion["n_propagation"])
            plate_invasion = passage_monoculture(plate_invasion, assumptions_invasion["dilution"])
        
        #  1 final growth cycle before storing data
        plate_invasion.Propagate(assumptions_invasion["n_propagation"])
		
        # find well with highest biomass
        dominant_index = np.where(np.sum(plate_invasion.N, axis = 0) == np.max(np.sum(plate_invasion.N, axis = 0)))[0][0] # Find the well with the highest biomass

        # Duplicate the chosen community  to the entire plate and save this in a data.frame to be add to as an attribute of the plate
        invader_N = pd.DataFrame()
        invader_R = pd.DataFrame()
        invader_R0 = pd.DataFrame()

        for i in range(assumptions["n_wells"]):
            invader_N["W" + str(i)] = plate_invasion.N["W" + str(dominant_index)]
            invader_R["W" + str(i)] = plate_invasion.R["W" + str(dominant_index)]
            invader_R0["W" + str(i)] = plate_invasion.R0["W" + str(dominant_index)]

        #Add the invasion plate to the attr of community
        setattr(plate, "invader_N", invader_N)
        setattr(plate, "invader_R", invader_R)
        setattr(plate, "invader_R0", invader_R0)
        setattr(plate, "isolate_abundance", np.sum(plate_invasion.N,axis=1)) 
        setattr(plate, "isolate_function", globals()[assumptions["selected_function"]](plate_invasion, params_simulation = assumptions))     
    
        print("\nFinished Stabilizing monoculture plate")
    return plate

 
def save_plate(assumptions, plate):
    """ 
    Save the initial plate in a pickle file. Like saving a frozen stock at -80C
    """
    if assumptions['save_plate']:
        import dill as pickle
        with open(assumptions['output_dir'] + assumptions['exp_id'] + ".p", "wb") as f:
            pickle.dump(plate, f)
   
   
def overwrite_plate(plate, assumptions):
    """ 
    Overwrite the plate N, R, and R0 dataframe by the input composition file
    """
    import os
    assert(os.path.isfile(assumptions['overwrite_plate'])), "The overwrite_plate does not exist"
    # Read the input data file
    df = pd.read_csv(assumptions["overwrite_plate"])
    
    # By default, use the latest transfer to avoid well name conflict
    df = df[df.Transfer == np.max(df.Transfer])]
    
    # If only one community, repeat filling this community into n_wells wells
    if len(df["Well"].unique()) == 1:
        temp_df = df.copy()
        for i in range(assumptions["n_wells"]):
            temp_df["Well"] = "W" + str(i)
            temp_df.assign(Well = "W" + str(i))
            df = pd.concat([df, temp_df])
    # If the input overwrite file has multiple communities, check if it has the same number as n_wells
    assert len(df["Well"].unique()) == assumptions["n_wells"], "overwrite_plate does not have the same number of wells as n_wells"
    # Check if the input file type has consumer, resurce and R0
    assert all(pd.Series(df["Type"].unique()).isin(["consumer", "resource", "R0"])), "overwrite_plate must have three types of rows: consumer, resource, R0"
    # Make empty dataframes
    N = plate.N.copy()
    R = plate.R.copy()
    R0 = plate.R.copy()
    # N0
    for w in range(assumptions["n_wells"]):
        temp_comm = df[(df["Well"] == ("W" + str(w))) & (df["Type"] == "consumer")][["ID", "Abundance"]]
        temp = np.zeros(N.shape[0])
        for i in range(temp_comm.shape[0]):
            temp[int(temp_comm.iloc[i]["ID"])] = temp_comm.iloc[i]["Abundance"]
            N["W" + str(w)] = temp
    # R
    for w in range(assumptions["n_wells"]):
        temp_res = df[(df["Well"] == ("W" + str(w))) & (df["Type"] == "resource")][["ID", "Abundance"]]
        temp = np.zeros(R.shape[0])
        for i in range(temp_res.shape[0]):
            temp[int(temp_res.iloc[i]["ID"])] = temp_res.iloc[i]["Abundance"]
            R["W" + str(w)] = temp
    # R0
    for w in range(assumptions["n_wells"]):
        temp_R0 = df[(df["Well"] == ("W" + str(w))) & (df["Type"] == "R0")][["ID", "Abundance"]]
        temp = np.zeros(R0.shape[0])
        for i in range(temp_R0.shape[0]):
            temp[int(temp_R0.iloc[i]["ID"])] = temp_R0.iloc[i]["Abundance"]
            R0["W" + str(w)] = temp
    plate.N = N
    plate.N0 = N
    plate.R = R
    plate.R0 = R0
    
    # Passaage the overwrite plate
    if assumptions["passage_overwrite_plate"]:
        plate.Passage(np.eye(assumptions["n_wells"]) * assumptions["dilution"])
    
    return(plate)
    
def prepare_experiment(assumptions):
    """
    Prepare the experimental setup for this simulation
    
    assumptions = dictionary of metaparameters
    
    Return: params, params_simulation, params_algorithm,plate
    """
    print("\nGenerate species paramaters")
    np.random.seed(assumptions['seed']) 
    params = MakeParams(assumptions) 
    
    print("\nDraw per-capita function and cost")
    function_species, function_interaction, function_interaction_p25 = draw_species_function(assumptions)
    params.update({"function_species": function_species, "function_interaction": function_interaction, "function_interaction_p25": function_interaction_p25})
    gi = draw_species_cost(function_species, assumptions)
    params.update({"g": gi})
    
    print("\nConstructing plate")
    np.random.seed(assumptions['seed']) 
    plate = make_plate(assumptions,params)
		
    print("\nAdd community function to plate")
    plate = add_community_function(plate, assumptions, params)
    
    if not pd.isnull(assumptions["overwrite_plate"]) :
        print("\nUpdating the initial plate composition by overwrite_plate")
        plate = overwrite_plate(plate, assumptions)
		
    print("\nPrepare Protocol")
	#Extract Protocol from protocol database
    algorithms = make_algorithms(assumptions)
    params_algorithm = algorithms[algorithms['algorithm_name'] == assumptions['protocol']]
    
    #Params_simulation by default  contains all assumptions not stored in params.
    params_simulation  =  dict((k, assumptions[k]) for k in assumptions.keys() if k not in params.keys())
    
    return params, params_simulation , params_algorithm, plate




