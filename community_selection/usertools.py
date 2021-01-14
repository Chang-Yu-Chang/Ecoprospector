#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mar 09 2020
@author: changyuchang
"""
import numpy as np
import pandas as pd
from community_selection.A_experiment_functions import *
from community_selection.B_community_phenotypes import *
from community_selection.C_selection_algorithms import *
from community_selection.D_perturbation_algorithms import *
from community_selection.E_protocols import *


def plot_community_function(function_df):
    """Plot community function"""
    function_df.plot.scatter(x = "Transfer", y = "CommunityPhenotype")

def plot_transfer_matrix(transfer_matrix):
    """Plot transfer matrix"""
    import seaborn as sns
    fig,ax=plt.subplots()
    sns.heatmap(transfer_matrix,ax=ax)
    ax.set_xlabel('Old well',fontsize=14)
    ax.set_ylabel('New well',fontsize=14)
    ax.set_title(r'Transfer Matrix',fontsize=14)
    plt.show()

def make_assumptions(input_file, row):
    '''  Generate the assumptions dictionary from input file and row of input file '''
    #Load row dat and default assumptions
    row_dat = pd.read_csv(input_file, keep_default_na=False).iloc[row]
    assumptions = a_default.copy()
    # load parameters used for make Params
    assumptions.update({"sampling_D": row_dat["sampling_D"], "fss": row_dat["fss"], "fsa": row_dat["fsa"], "fsw": row_dat["fsw"], "fas": row_dat["fas"], "faa": row_dat["faa"], "faw": row_dat["faw"], "fws": row_dat["fws"], "fwa": row_dat["fwa"], "fww": row_dat["fww"]})
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
    
    #If migration is True and no n_migration is set defaults to n_inoc
    if assumptions['migration']: 
        if pd.isnull(assumptions['n_migration']):
            assumptions['n_migration'] =assumptions['n_inoc']
        else:
            assumptions['n_migration'] = int(assumptions['n_migration'])
            
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
            
    # Overwrite plate
    if isinstance(assumptions["overwrite_plate"], str) and assumptions["overwrite_plate"] != "": 
        print("\nUpdating the n_wells with overwrite_plate")
        df = pd.read_csv(assumptions["overwrite_plate"])
        df = df[df.Transfer == np.max(df.Transfer)]
        if len(df["Well"].unique()) != 1:
            assumptions["n_wells"] = len(df["Well"].unique())
    
    if np.isnan(assumptions["ruggedness"]):
        assumptions["ruggedness"] = 0
    
    # f6_target_resource
    if "target_resource" in assumptions["selected_function"]:
        # Default target resource is the last resource
        if pd.isnull(assumptions['target_resource']):
            assumptions["target_resource"] = int(assumptions["rn"]) * int(assumptions["rf"]) - 1
        else:
            assumptions["target_resource"] = int(assumptions["target_resource"])
    
    return assumptions

def prepare_experiment(assumptions):
    """
    Prepare the experimental setup for this simulation
    
    assumptions = dictionary of metaparameters
    
    Return: params, params_simulation, params_algorithm,plate
    """
    print("\nGenerate species parameters")
    np.random.seed(assumptions['seed']) 
    params = MakeParams(assumptions) 
    if assumptions["selected_function"] == "f5_invader_suppression":
        print("\nDraw invader feature")
        params = create_invader(params, assumptions)
    
    print("\nDraw per-capita function and cost")
    f1_species_smooth, f1_species_rugged, f2_species_smooth, f2_species_rugged = draw_species_function(assumptions)
    params.update({"f1_species_smooth": f1_species_smooth, "f1_species_rugged": f1_species_rugged, "f2_species_smooth": f2_species_smooth, "f2_species_rugged": f2_species_rugged})
    gi = draw_species_cost(f1_species_smooth, assumptions)
    params.update({"g": gi})
    
    print("\nConstruct plate")
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

def simulate_community(params, params_simulation, params_algorithm, plate):
    """
    Simulate community dynamics by given experimental regimes
    
    params = parameter passed from community-simulator
    params_simulation = dictionary of parameters for running experiment
    params_algorithm = dictionary of algorithms that determine the selection regime, migration regime, and community pheotypes
    plate = Plate object specified by community-simulator
    
    Return:
    community_composition = concatenated, melted panda dataframe of community and resource composition in each transfer
    community_function = melted panda dataframe of community function
    """
    print("\nStarting " + params_simulation["exp_id"])
    print(params_algorithm)
    
    # Test the community function
    globals()[params_algorithm["community_phenotype"][0]](plate, params_simulation = params_simulation)
    try:
        community_function = globals()[params_algorithm["community_phenotype"][0]](plate, params_simulation = params_simulation) # Community phenotype
    except:
        print('\nCommunity phenotype test failed')
        raise SystemExit

    # Save the inocula composition
    if params_simulation['save_composition']:
        plate_data_list = list() # Plate composition
        plate_data = reshape_plate_data(plate, params_simulation,transfer_loop_index=0)  # Initial state
        plate_data_list.append(plate_data)
        composition_filename = params_simulation['output_dir'] + params_simulation['exp_id'] + '_composition.txt'   
        
    # Save the initial community function + richness + biomass
    if params_simulation['save_function']:
        community_function_list = list() # Plate composition
        richness = np.sum(plate.N >= 1/params_simulation["scale"], axis = 0) # Richness
        biomass = list(np.sum(plate.N, axis = 0)) # Biomass
        function_data = reshape_function_data(params_simulation,community_function, richness, biomass, transfer_loop_index =0)
        community_function_list.append(function_data)
        function_filename = params_simulation['output_dir'] + params_simulation['exp_id'] + '_function.txt'   

    print("\nStart propogation")
    # Run simulation
    for i in range(0, params_simulation["n_transfer"]):
        # Algorithms used in this transfer
        phenotype_algorithm = params_algorithm["community_phenotype"][i]
        selection_algorithm = params_algorithm["selection_algorithm"][i]

        # Propagation
        plate.Propagate(params_simulation["n_propagation"])

        # Measure Community phenotype
        community_function = globals()[phenotype_algorithm](plate, params_simulation = params_simulation) # Community phenotype
        
        # Append the composition to a list
        if params_simulation['save_composition'] and ((i+1) % params_simulation['composition_lograte'] == 0):
            plate_data = reshape_plate_data(plate, params_simulation, transfer_loop_index=i+1)  # Initial state
            plate_data_list.append(plate_data)

        if params_simulation['save_function'] and ((i+1) % params_simulation['function_lograte'] == 0):
            richness = np.sum(plate.N >= 1/params_simulation["scale"], axis = 0) # Richness
            biomass = list(np.sum(plate.N, axis = 0)) # Biomass
            function_data = reshape_function_data(params_simulation, community_function, richness, biomass, transfer_loop_index =i+1)
            community_function_list.append(function_data)

        #Store prior state before passaging (For coalescence)
        setattr(plate, "prior_N", plate.N)
        setattr(plate, "prior_R", plate.R)
        setattr(plate, "prior_R0", plate.R0)

        # Passage and transfer matrix
        transfer_matrix = globals()[selection_algorithm](community_function)
        if params_simulation['monoculture']:
            plate = passage_monoculture(plate, params_simulation["dilution"])
        else:
            plate.Passage(transfer_matrix * params_simulation["dilution"])
        
        # Perturbation
        if params_simulation['directed_selection']:
            if selection_algorithm == 'select_top': # In principle it can take select_top_x% but leave it as select_top for now
                plate = perturb(plate, params_simulation, keep = np.where(community_function >= np.max(community_function))[0][0])
            # if selection_algorithm != 'select_top' and (params_algorithm.iloc[i]["algorithm_name"] != 'simple_screening'):
            #   plate = perturb(plate, params_simulation, keep = None)
            elif selection_algorithm == "no_selection": 
                pass
        
        print("Transfer " + str(i+1))

    if params_simulation['save_composition']:
        pd.concat(plate_data_list).to_csv(composition_filename, index = False)
    if params_simulation['save_function']:
        pd.concat(community_function_list).to_csv(function_filename, index = False)
    print("\n" + params_simulation["exp_id"] + " finished")

def save_plate(assumptions, plate):
    """ 
    Save the initial plate in a pickle file. Like saving a frozen stock at -80C
    """
    if assumptions['save_plate']:
        import dill as pickle
        with open(assumptions['output_dir'] + assumptions['exp_id'] + ".p", "wb") as f:
            pickle.dump(plate, f)

def extract_species_function(assumptions):
    """
    Extract the per-capita species function from the community data
    """
    np.random.seed(assumptions['seed']) 
    params = MakeParams(assumptions) 
    f1_species_smooth, f1_species_rugged, f2_species_smooth, f2_species_rugged = draw_species_function(assumptions)
    S_tot = int(assumptions["sn"]) * int(assumptions["sf"]) + int(assumptions["Sgen"])
    
    if "additive" in assumptions["selected_function"]:
        if assumptions["selected_function"] == "f1_additive":
            per_capita_function = f1_species_smooth
            species_function = pd.DataFrame({"SelectedFunction": assumptions["selected_function"], "Seed": np.repeat(assumptions['seed'], S_tot), "ID": range(1, S_tot+1), "PerCapitaFunction": per_capita_function})
            if "cost" in assumptions["exp_id"]: # Should read a flag instead of name
                gi = draw_species_cost(f1_species_smooth, assumptions)
                params.update({"g": gi})
                species_function = pd.DataFrame({"SelectedFunction": assumptions["selected_function"], "Seed": np.repeat(assumptions['seed'], S_tot), "ID": range(1, S_tot+1), "PerCapitaFunction": per_capita_function, "g": gi})
        elif assumptions["selected_function"] == "f1a_additive":
            per_capita_function = f1_species_rugged
            species_function = pd.DataFrame({"SelectedFunction": assumptions["selected_function"], "Seed": np.repeat(assumptions['seed'], S_tot), "ID": range(1, S_tot+1), "PerCapitaFunction": per_capita_function})

    
    elif "interaction" in assumptions["selected_function"]:
        if assumptions["selected_function"] == "f2_interaction":
            per_interaction_function = f2_species_smooth
        elif assumptions["selected_function"] == "f2a_interaction":
            per_interaction_function = f2_species_rugged
            
        df_interaction_function = pd.DataFrame(per_interaction_function)
        df_interaction_function.columns = range(1, S_tot+1)
        df_interaction_function = df_interaction_function.assign(ID_row=range(1,S_tot+1)).melt(id_vars="ID_row", var_name = "ID_col", value_name = "PerCapitaFunction")
        df_interaction_function = df_interaction_function.assign(SelectedFunction = assumptions["selected_function"], Seed = assumptions['seed'])
        species_function = df_interaction_function[["SelectedFunction", "Seed", "ID_row", "ID_col", "PerCapitaFunction"]]
    
    return(species_function)


