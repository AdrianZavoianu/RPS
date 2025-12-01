import os
import sys

sibling_folder_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ETPS_Library'))
sys.path.append(sibling_folder_path)
import ETPS_Pushover as EP
import ETPS_Responses as ER

# Project Data
'To be implemented in each output filename'
project_name="160Wil"
base_story = 'L01'

#EP.extract_pushover_curves(project_name, base_story, 'x')
#EP.extract_pushover_curves(project_name, base_story, 'y')
#ER.get_displacements(project_name, 'x')
#ER.get_displacements(project_name, 'y')
#ER.get_drifts(project_name, 'x')
#ER.get_drifts(project_name, 'y')
#ER.get_storey_shears(project_name, 'x')
#ER.get_storey_shears(project_name, 'y')
#piles_joints_names=[16, 12, 23, 27, 6, 277, 20, 606, 4790, 571, 4794, 602, 4792]
#ER.get_joints_reactions(project_name,piles_joints_names)
#foundation_joints=[16, 12, 23, 27, 6, 277, 20, 606, 4790, 571, 4794, 602, 4792,463,8,762,249,740,206,310,2,702,172,706,395,176,1015,34,640,548,547]
#ER.get_joints_vertical_displacements(project_name,foundation_joints)
#ER.get_beams_hinges(project_name)
#ER.get_columns_hinges(project_name)
#ER.get_walls_quads_strain_rotations(project_name)
#ER.get_walls_piers_forces(project_name)
#ER.get_beams_forces(project_name)