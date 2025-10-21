import os

from ETDB_Library import ETDB_Functions as ETF

current_directory = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_directory)

# Project Data
'To be implemented in each output filename'

project="160Wil"
subfolder='DERG'
root_folder_path=os.path.join('ETDB_OUT_'+project,subfolder)

columns=[123,87,146]
# joints ID's as intergers
#piles=[16,12,23,27,6,277,20]
piles=[16, 12, 23, 27, 6, 277, 20, 606, 4790, 571, 4794, 602, 4792]
foundation_joints=[16, 12, 23, 27, 6, 277, 20, 606, 4790, 571, 4794, 602, 4792,463,8,762,249,740,206,310,2,702,172,706,395,176,1015,34,640,548,547]


# Retrive the results

ETF.get_story_drifts (root_folder_path,subfolder)
#ETF.get_joint_drifts (root_folder_path,subfolder)
#ETF.get_story_displacements(root_folder_path,subfolder)
ETF.get_story_accelerations(root_folder_path,subfolder)
#ETF.get_diaphragm_accelerations(root_folder_path,subfolder)
#ETF.get_joint_accelerations(root_folder_path,subfolder)
ETF.get_story_forces(root_folder_path,subfolder)

#ETF.get_joints_reactions(root_folder_path,subfolder,piles)
#ETF.get_joints_vertical_displacements(root_folder_path,subfolder,foundation_joints)

#ETF.get_beams_plastic_hinges(root_folder_path,subfolder)
#ETF.get_columns_plastic_hinges(root_folder_path,subfolder)
#ETF.get_quad_strain_rotations(root_folder_path,subfolder)

#ETF.get_columns_forces(root_folder_path,subfolder)
#ETF.get_pier_forces(root_folder_path,subfolder)
#ETF.get_beams_forces(root_folder_path,subfolder)


#ETF.get_links_forces(root_folder_path,subfolder,links)
#ETF.get_links_displacements(root_folder_path,subfolder,links)













