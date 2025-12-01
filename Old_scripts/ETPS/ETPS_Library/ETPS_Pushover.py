import logging
import os

import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#Get the path of the root directory of the project
current_file_path = os.path.abspath(__file__)
current_file_directory = os.path.dirname(current_file_path)
parent_directory = os.path.dirname(current_file_directory)

def extract_pushover_curves(project_name, base_story, direction):
    """
    Extracts pushover curves from an Excel file and saves the results to a new Excel file with each load case in a separate sheet.

    Parameters:
    file_path (str): Path to the input Excel file.
    base_story (str): The base story to filter the Story Forces data.
    direction (str): The direction of the pushover ('x' or 'y').

    Returns:
    dict: A dictionary containing the extracted data.
    """
    logging.info(f"Starting extraction of pushover curves for project '{project_name}', base story '{base_story}', direction '{direction}'.")
    col_disp, col_shear = get_columns_by_direction(direction)
    if col_disp is None or col_shear is None:
        logging.error(f"Invalid direction '{direction}' specified.")
        raise ValueError('Invalid direction specified.')

    #Dymamically configure the path to the project's input and output directories
    input_path = os.path.join(parent_directory,f'ETPS_OUT_{project_name}','Input','Pushover')
    output_path = os.path.join(parent_directory,f'ETPS_OUT_{project_name}','Results','Pushover',f'{project_name}_Push_Curves_{direction.upper()} direction.xlsx')

    logging.info(f"Input path: {input_path}")
    logging.info(f"Output path: {output_path}")


    if not os.path.exists(input_path):
            logging.error(f"Input directory not found: {input_path}")
            raise FileNotFoundError(f"Input file not found: {input_path}. Check the name of the project folder or if any input file is added")

    results = {}

    file_path=get_input_file(input_path)
    logging.info(f"Using input file: {file_path}")
    excel_file_data = pd.ExcelFile(file_path)

    disp_df = process_displacements(excel_file_data, col_disp)
    results = group_data(disp_df, col_disp, direction)
    for case_name, data in results.items():
        if col_disp in data and len(data[col_disp]) > 0:
            initial_value = data[col_disp][0]
            # Normalize first (retain sign), then take absolute values
            data[col_disp] = [abs(val - initial_value) for val in data[col_disp]]
    
    shear_df = process_shear(excel_file_data, base_story, col_shear)
    results = group_data(shear_df, col_shear, direction, results)
    save_to_excel(results, output_path)

    logging.info(f"Extraction and saving completed successfully. Results saved to {output_path}")
    return results

def get_columns_by_direction(direction):
    """
    Returns the displacement and shear column names based on the direction.

    Parameters:
    direction (str): The direction of the pushover ('x' or 'y').

    Returns:
    tuple: A tuple containing the displacement and shear column names.
    """
    logging.debug(f"Getting column names for direction '{direction}'.")
    if direction == 'x':
        return 'Ux', 'VX'
    elif direction == 'y':
        return 'Uy', 'VY'
    else:
        return None, None

def process_displacements(excel_file_data, col_disp):
    """
    Processes the Joint Displacements sheet.

    Parameters:
    excel_file_data (pd.ExcelFile): The Excel file data.
    col_disp (str): The displacement column name.

    Returns:
    pd.DataFrame: The processed displacements DataFrame.
    """
    logging.info("Processing displacements.")
    disp_df = pd.read_excel(excel_file_data, sheet_name='Joint Displacements', header=1)
    disp_df = disp_df.drop(0)
    disp_df = disp_df[['Output Case', 'Step Number', col_disp]]
    disp_df[col_disp] = pd.to_numeric(disp_df[col_disp], errors='coerce').round(0)
    logging.debug("Displacements processed successfully.")
    return disp_df

def process_shear(excel_file_data, base_story, col_shear):
    """
    Processes the Story Forces sheet.

    Parameters:
    excel_file_data (pd.ExcelFile): The Excel file data.
    base_story (str): The base story to filter the Story Forces data.
    col_shear (str): The shear column name.

    Returns:
    pd.DataFrame: The processed shear DataFrame.
    """
    logging.info(f"Processing shear for base story '{base_story}'.")
    shear_df = pd.read_excel(excel_file_data, sheet_name='Story Forces', header=1)
    shear_df = shear_df.drop(0)
    if base_story not in shear_df['Story'].values:
        logging.error(f"Base story '{base_story}' not found in the Story Forces data.")
        raise ValueError(f"Base story '{base_story}' not found in the Story Forces data. Check the storey names.")
    shear_df = shear_df[(shear_df['Location'] == 'Bottom') & (shear_df['Story'] == base_story)]
    shear_df = shear_df[['Output Case', 'Step Number', col_shear]]
    shear_df[col_shear] = pd.to_numeric(shear_df[col_shear], errors='coerce').abs().round(0)
    logging.debug("Shear processed successfully.")
    return shear_df

def group_data(df, col_name, direction, results=None):
    """
    Groups the DataFrame by Output Case and stores the results in a dictionary.

    Parameters:
    df (pd.DataFrame): The DataFrame to group.
    col_name (str): The column name to include in the results.
    direction (str): The direction of the pushover ('x' or 'y').
    results (dict): The dictionary to store the results. If None, a new dictionary is created.

    Returns:
    dict: The dictionary containing the grouped data.
    """
    logging.info(f"Grouping data for direction '{direction}'.")
    if results is None:
        results = {}

    grouped = df.groupby('Output Case')
    for output_case, group in grouped:
        if (direction == 'x' and 'Y' in output_case) or (direction == 'y' and 'X' in output_case):
            logging.debug(f"Skipping output case '{output_case}' for direction '{direction}'.")
            continue  # Skip this output case if it contains 'Y' in 'x' direction or 'X' in 'y' direction

        if output_case not in results:
            results[output_case] = {}
        results[output_case]['Step Number'] = group['Step Number'].tolist()
        results[output_case][col_name] = group[col_name].tolist()
    logging.debug(f"Grouping completed for direction '{direction}'.")
    return results

def save_to_excel(results, output_path):
    """
    Saves the results dictionary to an Excel file with each Output Case in a separate sheet.

    Parameters:
    results (dict): The dictionary containing the results.
    output_path (str): The path to the output Excel file.
    """
    logging.info(f"Saving results to Excel at '{output_path}'.")
    with pd.ExcelWriter(output_path) as writer:
        for output_case, data in results.items():
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name=output_case, index=False)
    logging.info(f"Results saved successfully to '{output_path}'.")

def get_input_file(input_directory):
    """
    Gets the first file in the input directory.

    Parameters:
    input_directory (str): The path to the input directory.

    Returns:
    str: The input file path.
    """
    logging.info(f"Retrieving input file from directory: {input_directory}.")
    input_files = os.listdir(input_directory)
    if input_files:
        input_file = input_files[0]
        input_file_path = os.path.join(input_directory, input_file)
        logging.debug(f"Found input file: {input_file_path}.")
        return input_file_path
    else:
        logging.error(f"No input files found in the directory: {input_directory}.")
        raise FileNotFoundError("No input files found in the Input directory.")