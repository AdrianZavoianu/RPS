import logging
import os

import pandas as pd

from ETPS_Pushover import get_input_file

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get the path of the root directory of the project
current_file_path = os.path.abspath(__file__)
current_file_directory = os.path.dirname(current_file_path)
parent_directory = os.path.dirname(current_file_directory)

def get_displacements(project_name, direction):
    """
    Calculate and save the maximum absolute displacements for each story and load case.

    Parameters:
    project_name (str): The name of the project.
    direction (str): The direction of displacement ('x' or 'y').

    Raises:
    ValueError: If an invalid direction is specified.
    """
    # Dynamically configure the path to the project's input and output directories
    input_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Input', 'Responses')
    output_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Results', 'Displacements', f'{project_name}_Displacements_{direction.upper()} direction.xlsx')

    if not os.path.exists(input_path):
            logging.error(f"Input directory not found: {input_path}")
            raise FileNotFoundError(f"Input file not found: {input_path}. Check the name of the project folder or if any input file is added") 

    # Get the input file path
    file_path = get_input_file(input_path)
    logging.info(f"Using input file: {file_path}")
    logging.info(f"Output path: {output_path}")

    # Read the Excel file
    excel_file_data = pd.ExcelFile(file_path)
    disp_df = pd.read_excel(excel_file_data, sheet_name='Joint Displacements', header=1)
    disp_df = disp_df.drop(0)  # Drop the first row if it is not needed

    # Filter and select the appropriate displacement column based on the direction
    if direction == 'x':
        col_disp = 'Ux'
        disp_df = disp_df[~disp_df['Output Case'].str.contains('Y')]
    elif direction == 'y':
        col_disp = 'Uy'
        disp_df = disp_df[~disp_df['Output Case'].str.contains('X')]
    else:
        logging.error(f"Invalid direction '{direction}' specified.")
        raise ValueError('Invalid direction specified.')

    # Select relevant columns
    disp_df = disp_df[['Story', 'Output Case', 'Step Type', col_disp]]

    # Calculate the maximum absolute displacement for each story and each load case
    max_abs_disp = disp_df.groupby(['Story', 'Output Case'])[col_disp].apply(lambda x: x.abs().max()).unstack().reset_index()
    max_abs_disp.columns.name = None  # Remove the index name

    # Save the result to an Excel file
    max_abs_disp.to_excel(output_path, index=False)
    logging.info(f"Saved maximum absolute displacements to: {output_path}")


def get_drifts(project_name,direction):

    # Dynamically configure the path to the project's input and output directories
    input_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Input', 'Responses')
    output_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Results', 'Drifts', f'{project_name}_Drifts_{direction.upper()} direction.xlsx')

    if not os.path.exists(input_path):
            logging.error(f"Input directory not found: {input_path}")
            raise FileNotFoundError(f"Input file not found: {input_path}. Check the name of the project folder or if any input file is added") 

    # Get the input file path
    file_path = get_input_file(input_path)
    logging.info(f"Using input file: {file_path}")
    logging.info(f"Output path: {output_path}")

    # Read the Excel file
    excel_file_data = pd.ExcelFile(file_path)
    drifts_df = pd.read_excel(excel_file_data, sheet_name='Story Drifts', header=1)
    drifts_df = drifts_df.drop(0)  # Drop the first row if it is not needed

    # Select relevant columns
    drifts_df = drifts_df[['Story', 'Output Case', 'Step Type', 'Direction', 'Drift']]

    # Filter and select the appropriate displacement column based on the direction
    if direction == 'x':
        drifts_df = drifts_df[~drifts_df['Output Case'].str.contains('Y')]
        drifts_df = drifts_df[~drifts_df['Direction'].str.contains('Y')]
    elif direction == 'y':
        drifts_df = drifts_df[~drifts_df['Output Case'].str.contains('X')]
        drifts_df = drifts_df[~drifts_df['Direction'].str.contains('X')]
    else:
        logging.error(f"Invalid direction '{direction}' specified.")
        raise ValueError('Invalid direction specified.')

    max_drifts = drifts_df.groupby(['Story', 'Output Case'])['Drift'].apply(lambda x: x.max()).unstack().reset_index()

    # Save the result to an Excel file
    max_drifts.to_excel(output_path, index=False)
    logging.info(f"Saved maximum drifts to: {output_path}")

def get_storey_shears(project_name,direction):

    # Dynamically configure the path to the project's input and output directories
    input_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Input', 'Responses')
    output_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Results', 'Storey Shears', f'{project_name}_Storey Shears_{direction.upper()} direction.xlsx')

    if not os.path.exists(input_path):
            logging.error(f"Input directory not found: {input_path}")
            raise FileNotFoundError(f"Input file not found: {input_path}. Check the name of the project folder or if any input file is added") 

    # Get the input file path
    file_path = get_input_file(input_path)
    logging.info(f"Using input file: {file_path}")
    logging.info(f"Output path: {output_path}")

    # Read the Excel file
    excel_file_data = pd.ExcelFile(file_path)
    shears_df = pd.read_excel(excel_file_data, sheet_name='Story Forces', header=1)
    shears_df = shears_df.drop(0)  # Drop the first row if it is not needed

    # Filter and select the appropriate displacement column based on the direction
    if direction == 'x':
        col_shear = 'VX'
        shears_df = shears_df[~shears_df['Output Case'].str.contains('Y')]
    elif direction == 'y':
        col_shear = 'VY'
        shears_df = shears_df[~shears_df['Output Case'].str.contains('X')]
    else:
        logging.error(f"Invalid direction '{direction}' specified.")
        raise ValueError('Invalid direction specified.')

    shears_df = shears_df[~shears_df['Location'].str.contains('Top')]

    # Select relevant columns
    shears_df = shears_df[['Story', 'Output Case', 'Step Type', 'Location', col_shear]]

    max_shears = shears_df.groupby(['Story', 'Output Case'])[col_shear].apply(lambda x: x.abs().max()).unstack().reset_index()

    # Save the result to an Excel file
    max_shears.to_excel(output_path, index=False)
    logging.info(f"Saved maximum shears to: {output_path}")


def get_joints_reactions(project_name,joints_names):

    # Dynamically configure the path to the project's input and output directories
    input_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Input', 'Responses')
    output_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Results', 'Foundation', f'{project_name}_Piles Reactions')

    if not os.path.exists(input_path):
            logging.error(f"Input directory not found: {input_path}")
            raise FileNotFoundError(f"Input file not found: {input_path}. Check the name of the project folder or if any input file is added") 

    # Get the input file path
    file_path = get_input_file(input_path)
    logging.info(f"Using input file: {file_path}")
    logging.info(f"Output path: {output_path}")

    # Read the Excel file
    excel_file_data = pd.ExcelFile(file_path)
    piles_forces_df = pd.read_excel(excel_file_data, sheet_name='Joint Reactions', header=1)
    df = piles_forces_df.drop(0)  # Drop the first row if it is not needed
    loadcases=df['Output Case'].unique()
    for step_type in ['Max','Min']:
        values_df=pd.DataFrame()
        values_df.insert(loc=0,column='Joint ID',value=joints_names)
        for case in loadcases:
            values=[]
            for item in joints_names:
                fil=df.loc[(df['Output Case']==case)&(df['Step Type']==step_type)&(df['Unique Name']==item)]
                max_value=fil['FZ'].max()
                values.append(round(max_value,0))
            values_df[case]=values

        values_df['Max']=values_df.iloc[:,1:].max(axis=1)
        values_df['Min']=values_df.iloc[:,1:].min(axis=1)
        print(values_df)
        values_df.to_excel(output_path+'_N_'+step_type+'.xlsx',index=False)

def get_joints_vertical_displacements(project_name,joints_names):

    # Dynamically configure the path to the project's input and output directories
    input_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Input', 'Responses')
    output_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Results', 'Foundation', f'{project_name}_Foundation Displacements')

    if not os.path.exists(input_path):
            logging.error(f"Input directory not found: {input_path}")
            raise FileNotFoundError(f"Input file not found: {input_path}. Check the name of the project folder or if any input file is added") 

    # Get the input file path
    file_path = get_input_file(input_path)
    logging.info(f"Using input file: {file_path}")
    logging.info(f"Output path: {output_path}")

    # Read the Excel file
    excel_file_data = pd.ExcelFile(file_path)
    fou_disp_df = pd.read_excel(excel_file_data, sheet_name='Joint Displacements', header=1)
    df = fou_disp_df.drop(0)  # Drop the first row if it is not needed
    loadcases=df['Output Case'].unique()
    for step_type in ['Max','Min']:
        values_z_df=pd.DataFrame()
        values_z_df.insert(loc=0,column='Joints',value=joints_names)

        for case in loadcases:
            values_z=[]
            for item in joints_names:
                fil=df.loc[(df['Output Case']==case)&(df['Step Type']==step_type)&(df['Unique Name']==item)]
                if(step_type=='Max'):
                    disp_z=fil['Uz'].max()
                else:
                    disp_z=fil['Uz'].min()
                values_z.append(round(disp_z,1))
            values_z_df[case]=values_z

        values_z_df['Max']=values_z_df.iloc[:,1:].max(axis=1)
        values_z_df['Min']=values_z_df.iloc[:,1:].min(axis=1)
        print(values_z_df)
        values_z_df.to_excel(output_path+'_'+step_type+'.xlsx',index=False)


def get_beams_hinges(project_name):

    # Dynamically configure the path to the project's input and output directories
    input_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Input', 'Responses')
    output_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Results', 'Beams', f'{project_name}_Beam Hinges')

    if not os.path.exists(input_path):
            logging.error(f"Input directory not found: {input_path}")
            raise FileNotFoundError(f"Input file not found: {input_path}. Check the name of the project folder or if any input file is added") 

    # Get the input file path
    file_path = get_input_file(input_path)
    logging.info(f"Using input file: {file_path}")
    logging.info(f"Output path: {output_path}")

    # Read the Excel file
    excel_file_data = pd.ExcelFile(file_path)
    beams_hinges_df = pd.read_excel(excel_file_data, sheet_name='Hinge States', header=1)
    df = beams_hinges_df.drop(0)  # Drop the first row if it is not needed
    loadcases=df['Output Case'].unique()
    df_red=df.loc[(df['Output Case']==loadcases[0])]

    values_df=pd.DataFrame()
    values_df['Story']=df_red['Story']
    values_df['Frame/Wall']=df_red['Frame/Wall']
    values_df['Unique Name']=df_red['Unique Name']
    values_df['Step Type']=df_red['Step Type']
    values_df['Hinge']=df_red['Hinge']
    values_df['Hinge ID']=df_red['Generated Hinge']
    values_df['Rel Dist']=df_red['Rel Dist']
    for case in loadcases:
        fil=df.loc[(df['Output Case']==case)]
        values=(fil['R3 Plastic']).tolist()
        values_df[case]=values

    values_df['Max']=values_df.iloc[:,7:].max(axis=1)
    values_df['Min']=values_df.iloc[:,7:].min(axis=1)
    print(values_df)
    values_df.to_excel(output_path+'.xlsx',index=False)


def get_columns_hinges(project_name):

    # Dynamically configure the path to the project's input and output directories
    input_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Input', 'Responses')
    output_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Results', 'Columns', f'{project_name}_Columns Hinges')

    if not os.path.exists(input_path):
            logging.error(f"Input directory not found: {input_path}")
            raise FileNotFoundError(f"Input file not found: {input_path}. Check the name of the project folder or if any input file is added") 

    # Get the input file path
    file_path = get_input_file(input_path)
    logging.info(f"Using input file: {file_path}")
    logging.info(f"Output path: {output_path}")

    # Read the Excel file
    excel_file_data = pd.ExcelFile(file_path)
    hinges_df = pd.read_excel(excel_file_data, sheet_name='Fiber Hinge States', header=1)
    df = hinges_df.drop(0)  # Drop the first row if it is not needed
    loadcases=df['Output Case'].unique()
    df_red=df.loc[(df['Output Case']==loadcases[0])]
    col_ID=df_red['Frame/Wall'].unique()

    values_df=pd.DataFrame()
    rotations=['R2','R3']

    for rot in rotations:
        for step_type in ['Max','Min']:
            values_df=pd.DataFrame()
            is_first_case=True
            for case in loadcases:
                values=[]
                names=[]
                ids=[]
                for item in col_ID:
                    fil=df.loc[(df['Output Case']==case)&(df['Step Type']==step_type)&(df['Frame/Wall']==item)]
                    unique_names=fil['Unique Name'].unique().tolist()
                    unique_names.reverse()
                    for un in unique_names:
                        fil_names=fil.loc[(fil['Unique Name']==un)]
                        selected_value=0
                        if step_type=='Max':
                            selected_value=fil_names[rot].max()
                        else:
                            selected_value=fil_names[rot].min()
                        if is_first_case:
                            names.append(item)
                            ids.append(un)

                        values.append(selected_value)
                if is_first_case:
                    values_df['Column']=names
                    values_df['Unique Name']=ids
                is_first_case=False
                values_df[case]=values
            values_df['Max']=values_df.iloc[:,2:].max(axis=1)
            values_df['Min']=values_df.iloc[:,2:].min(axis=1)
            print(values_df)
            values_df.to_excel(output_path+'_'+rot+step_type+'.xlsx',index=False)

def get_walls_quads_strain_rotations(project_name):

    # Dynamically configure the path to the project's input and output directories
    input_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Input', 'Responses')
    output_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Results', 'Walls', f'{project_name}_Walls Rotations')

    if not os.path.exists(input_path):
            logging.error(f"Input directory not found: {input_path}")
            raise FileNotFoundError(f"Input file not found: {input_path}. Check the name of the project folder or if any input file is added") 

    # Get the input file path
    file_path = get_input_file(input_path)
    logging.info(f"Using input file: {file_path}")
    logging.info(f"Output path: {output_path}")

    # Read the Excel file
    excel_file_data = pd.ExcelFile(file_path)
    quads_df = pd.read_excel(excel_file_data, sheet_name='Quad Strain Gauge - Rotation', header=1)
    df = quads_df.drop(0)  # Drop the first row if it is not needed
    loadcases=df['Output Case'].unique()
    values_df=pd.DataFrame()
    is_first_case=True
    for step_type in ['Max','Min']:
        for case in loadcases:
            fil=df.loc[(df['Output Case']==case)&(df['StepType']==step_type)]
            if is_first_case:
                values_df['Story']=fil['Story']
                values_df['Name']=fil['Name']
                is_first_case=False
            values=(fil['Rotation']).tolist()
            values_df[case]=values

        values_df['Max']=values_df.iloc[:,7:].max(axis=1)
        values_df['Min']=values_df.iloc[:,7:].min(axis=1)
        print(values_df)
        values_df.to_excel(output_path+'_'+step_type+'.xlsx',index=False)

def get_walls_piers_forces(project_name):

    # Dynamically configure the path to the project's input and output directories
    input_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Input', 'Responses')
    output_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Results', 'Walls', f'{project_name}')

    if not os.path.exists(input_path):
            logging.error(f"Input directory not found: {input_path}")
            raise FileNotFoundError(f"Input file not found: {input_path}. Check the name of the project folder or if any input file is added") 

    # Get the input file path
    file_path = get_input_file(input_path)
    logging.info(f"Using input file: {file_path}")
    logging.info(f"Output path: {output_path}")

    # Read the Excel file
    excel_file_data = pd.ExcelFile(file_path)
    quads_df = pd.read_excel(excel_file_data, sheet_name='Pier Forces', header=1)
    df = quads_df.drop(0)  # Drop the first row if it is not needed
    loadcases=df['Output Case'].unique()
    piers=df['Pier'].unique()
    values_df=pd.DataFrame()
    forces=['P','V2','V3','M2','M3']
    for force in forces:
        for step_type in ['Max','Min']:
            values_df=pd.DataFrame()
            is_first_case=True
            for case in loadcases:
                values=[]
                if is_first_case:
                    names=[]
                    storeys=[]
                for item in piers:
                    fil=df.loc[(df['Pier']==item)]
                    floors=fil['Story'].unique().tolist()
                    floors.reverse()
                    for story in floors:
                        fil=df.loc[(df['Output Case']==case)&(df['Step Type']==step_type)&(df['Pier']==item)&(df['Location']=='Bottom')&(df['Story']==story)]
                        values.append(fil[force].max())
                        if is_first_case:
                            names.append(item)
                            storeys.append(story)
                if is_first_case:
                    values_df['Pier']=names
                    values_df['Story']=storeys
                    is_first_case=False
                values_df[case]=values
            values_df['Max']=values_df.iloc[:,2:].max(axis=1)
            values_df['Min']=values_df.iloc[:,2:].min(axis=1)
            print(values_df)
            values_df.to_excel(output_path+'_'+force+'_'+step_type+'.xlsx')

def get_beams_forces(project_name):

    # Dynamically configure the path to the project's input and output directories
    input_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Input', 'Responses')
    output_path = os.path.join(parent_directory, f'ETPS_OUT_{project_name}', 'Results', 'Beams', f'{project_name}')

    if not os.path.exists(input_path):
            logging.error(f"Input directory not found: {input_path}")
            raise FileNotFoundError(f"Input file not found: {input_path}. Check the name of the project folder or if any input file is added") 

    # Get the input file path
    file_path = get_input_file(input_path)
    logging.info(f"Using input file: {file_path}")
    logging.info(f"Output path: {output_path}")

    # Read the Excel file
    excel_file_data = pd.ExcelFile(file_path)
    beams_hinges_df = pd.read_excel(excel_file_data, sheet_name='Element Forces - Beams', header=1)
    df = beams_hinges_df.drop(0)  # Drop the first row if it is not needed
    loadcases=df['Output Case'].unique()
    bea_ID=df['Beam'].unique()
    values_df=pd.DataFrame()
    forces=['P','V2','V3','M2','M3']

    for force in forces:
        for step_type in ['Max','Min']:
            values_df=pd.DataFrame()
            is_first_case=True
            for case in loadcases:
                values=[]
                names=[]
                ids=[]
                for item in bea_ID:
                    fil=df.loc[(df['Output Case']==case)&(df['Step Type']==step_type)&(df['Beam']==item)]
                    unique_names=fil['Unique Name'].unique().tolist()
                    unique_names.reverse()
                    for un in unique_names:
                        fil_names=fil.loc[(fil['Unique Name']==un)]
                        selected_value=0
                        if force=='P':
                            if step_type=='Max':
                                selected_value=fil_names[force].max()
                            else:
                                selected_value=fil_names[force].min()
                        else:
                            selected_value=fil_names[force].abs().max()

                        if is_first_case:
                            names.append(item)
                            ids.append(un)
                        values.append(round(selected_value,0))
                if is_first_case:
                    values_df['Beam']=names
                    values_df['Unique Name']=ids
                is_first_case=False
                values_df[case]=values
            values_df['Max']=values_df.iloc[:,2:].max(axis=1)
            values_df['Min']=values_df.iloc[:,2:].min(axis=1)
            print(values_df)
            values_df.to_excel(output_path+'_'+force+'_'+step_type+'.xlsx')
