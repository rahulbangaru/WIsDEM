try:
    import ruamel_yaml as ry
except:
    try:
        import ruamel.yaml as ry
    except:
        raise ImportError('No module named ruamel.yaml or ruamel_yaml')

from scipy.interpolate import PchipInterpolator, Akima1DInterpolator, interp1d, RectBivariateSpline
import numpy as np
import jsonschema as json
import time
from openmdao.api import ExplicitComponent, Group, IndepVarComp, Problem


class Wind_Turbine(object):
    # Pure python class to load the input yaml file and break into few sub-dictionaries, namely:
    #   - wt_init_options: dictionary with all the inputs that will be passed as options to the openmdao components, such as the length of the arrays
    #   - blade: dictionary representing the entry blade in the yaml file
    #   - tower: dictionary representing the entry tower in the yaml file
    #   - nacelle: dictionary representing the entry nacelle in the yaml file
    #   - materials: dictionary representing the entry materials in the yaml file
    #   - airfoils: dictionary representing the entry airfoils in the yaml file

    def __init__(self):

        # Validate input file against JSON schema
        self.validate        = True        # (bool) run IEA turbine ontology JSON validation
        self.fname_schema    = ''          # IEA turbine ontology JSON schema file

        self.verbose         = False
        

    def initialize(self, fname_input):
        if self.verbose:
            print('Running initialization: %s' % fname_input)

        # Load input
        self.fname_input = fname_input
        self.wt_ref = self.load_ontology(self.fname_input, validate=self.validate, fname_schema=self.fname_schema)

        wt_init_options = self.openmdao_vectors()        
        blade           = self.wt_ref['components']['blade']
        tower           = {} # self.wt_ref['components']['tower']
        nacelle         = {} # self.wt_ref['components']['tower']
        materials       = self.wt_ref['materials']
        airfoils        = self.wt_ref['airfoils']
        

        return wt_init_options, blade, tower, nacelle, materials, airfoils
    
    def openmdao_vectors(self):
    
        wt_init_options = {}
        
        # Materials
        wt_init_options['materials']          = {}
        wt_init_options['materials']['n_mat'] = len(self.wt_ref['materials'])
        
        # Airfoils
        wt_init_options['airfoils']           = {}
        wt_init_options['airfoils']['n_af']   = len(self.wt_ref['airfoils'])
        wt_init_options['airfoils']['n_aoa']  = 200
        wt_init_options['airfoils']['n_Re']   = 1
        wt_init_options['airfoils']['n_tab']  = 1
        wt_init_options['airfoils']['n_xy']   = 200
        
        return wt_init_options

    def load_ontology(self, fname_input, validate=False, fname_schema=''):
        """ Load inputs IEA turbine ontology yaml inputs, optional validation """
        # Read IEA turbine ontology yaml input file
        t_load = time.time()
        with open(fname_input, 'r') as myfile:
            inputs = myfile.read()

        # Validate the turbine input with the IEA turbine ontology schema
        yaml = ry.YAML()
        if validate:
            t_validate = time.time()

            with open(fname_schema, 'r') as myfile:
                schema = myfile.read()
            json.validate(yaml.load(inputs), yaml.load(schema))

            t_validate = time.time()-t_validate
            if self.verbose:
                print('Complete: Schema "%s" validation: \t%f s'%(fname_schema, t_validate))
        else:
            t_validate = 0.

        if self.verbose:
            t_load = time.time() - t_load - t_validate
            print('Complete: Load Input File: \t%f s'%(t_load))
        
        return yaml.load(inputs)
        
        
class Materials(ExplicitComponent):
    # Openmdao component with the wind turbine materials coming from the input yaml file. The inputs and outputs are arrays where each entry represents a material
    
    def initialize(self):
        self.options.declare('mat_init_options')
    
    def setup(self):
        
        mat_init_options = self.options['mat_init_options']
        self.n_mat = n_mat = mat_init_options['n_mat']
        
        self.add_discrete_input('name', val=n_mat * [''],                         desc='Array of names of materials.')
        self.add_discrete_input('orth', val=np.zeros(n_mat),                      desc='Array of flags to set whether a material is isotropic (0) or orthtropic (1). Each entry represents a material.')
        self.add_discrete_input('component_id', val=np.zeros(n_mat),              desc='Array of flags to set whether a material is used in a blade: 0 - coating, 1 - sandwich filler , 2 - shell skin, 3 - shear webs, 4 - spar caps, 5 - TE reinf.isotropic.')
        
        self.add_input('E',             val=np.zeros([n_mat, 3]), units='Pa',     desc='Matrix of the Youngs moduli of the materials. Each row represents a material, the three columns represent E11, E22 and E33.')
        self.add_input('G',             val=np.zeros([n_mat, 3]), units='Pa',     desc='Matrix of the shear moduli of the materials. Each row represents a material, the three columns represent G12, G13 and G23.')
        self.add_input('nu',            val=np.zeros([n_mat, 3]),                 desc='Matrix of the Poisson ratio of the materials. Each row represents a material, the three columns represent nu12, nu13 and nu23.')
        self.add_input('rho',           val=np.zeros(n_mat),      units='kg/m**3',desc='Array of the density of the materials. For composites, this is the density of the laminate.')
        self.add_input('unit_cost',     val=np.zeros(n_mat),      units='USD/kg', desc='Array of the unit costs of the materials.')
        self.add_input('waste',         val=np.zeros(n_mat),                      desc='Array of the non-dimensional waste fraction of the materials.')
        self.add_input('rho_fiber',     val=np.zeros(n_mat),      units='kg/m**3',desc='Array of the density of the fibers of the materials.')
        self.add_input('rho_area_dry',  val=np.zeros(n_mat),      units='kg/m**2',desc='Array of the dry aerial density of the composite fabrics. Non-composite materials are kept at 0.')
        
        self.add_output('ply_t',        val=np.zeros(n_mat),      units='m',      desc='Array of the ply thicknesses of the materials. Non-composite materials are kept at 0.')
        self.add_output('fvf',          val=np.zeros(n_mat),                      desc='Array of the non-dimensional fiber volume fraction of the composite materials. Non-composite materials are kept at 0.')
        self.add_output('fwf',          val=np.zeros(n_mat),                      desc='Array of the non-dimensional fiber weight- fraction of the composite materials. Non-composite materials are kept at 0.')
        
    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        
        density_resin = 0.
        for i in range(self.n_mat):
            if discrete_inputs['name'][i] == 'resin':
                density_resin = inputs['rho'][i]
                id_resin = i
        if density_resin==0.:
            exit('Error: a material named resin must be defined in the input yaml')
        
        fvf   = np.zeros(self.n_mat)
        fwf   = np.zeros(self.n_mat)
        ply_t = np.zeros(self.n_mat)
        
        for i in range(self.n_mat):
            if discrete_inputs['component_id'][i] > 1: # It's a composite
                # Formula to estimate the fiber volume fraction fvf from the laminate and the fiber densities
                fvf[i]  = (inputs['rho'][i] - density_resin) / (inputs['rho_fiber'][i] - density_resin) 
                if outputs['fvf'][i] > 0.:
                    if abs(fvf[i] - outputs['fvf'][i]) > 1e-3:
                        exit('Error: the fvf of composite ' + discrete_input['name'][i] + ' specified in the yaml is equal to '+ str(outputs['fvf'][i] * 100) + '%, but this value is not compatible to the other values provided. It should instead be equal to ' + str(fvf[i]*100.) + '%')
                else:
                    outputs['fvf'][i] = fvf[i]
                # Formula to estimate the fiber weight fraction fwf from the fiber volume fraction and the fiber densities
                fwf[i]  = inputs['rho_fiber'][i] * outputs['fvf'][i] / (density_resin + ((inputs['rho_fiber'][i] - density_resin) * outputs['fvf'][i]))
                if outputs['fwf'][i] > 0.:
                    if abs(fwf[i] - outputs['fwf'][i]) > 1e-3:
                        exit('Error: the fwf of composite ' + discrete_input['name'][i] + ' specified in the yaml is equal to '+ str(outputs['fwf'][i] * 100) + '%, but this value is not compatible to the other values provided. It should instead be equal to ' + str(fwf[i]*100.) + '%')
                else:
                    outputs['fwf'][i] = fwf[i]
                # Formula to estimate the plyt thickness ply_t of a laminate from the aerial density, the laminate density and the fiber weight fraction
                ply_t[i] = inputs['rho_area_dry'][i] / inputs['rho'][i] / outputs['fwf'][i]
                if outputs['ply_t'][i] > 0.:
                    if abs(ply_t[i] - outputs['ply_t'][i]) > 1e-3:
                        exit('Error: the ply_t of composite ' + discrete_input['name'][i] + ' specified in the yaml is equal to '+ str(outputs['ply_t'][i]) + 'm, but this value is not compatible to the other values provided. It should instead be equal to ' + str(ply_t[i]) + 'm')
                else:
                    outputs['ply_t'][i] = ply_t[i]
        
        
        
        
class Airfoils(ExplicitComponent):
    def initialize(self):
        self.options.declare('af_init_options')
    
    def setup(self):
        af_init_options = self.options['af_init_options']
        n_af            = af_init_options['n_af'] # Number of airfoils
        n_aoa           = af_init_options['n_aoa']# Number of angle of attacks
        n_Re            = af_init_options['n_Re'] # Number of Reynolds, so far hard set at 1
        n_tab           = af_init_options['n_tab']# Number of tabulated data. For distributed aerodynamic control this could be > 1
        n_xy            = af_init_options['n_xy'] # Number of coordinate points to describe the airfoil geometry
        
        # Airfoil properties
        self.add_input('af_aoa', val=np.zeros(n_aoa),        units='deg',   desc='Grid of the angles of attack used to define the polars of the airfoils. All airfoils defined in openmdao share this grid.')
        self.add_input('af_Re',  val=np.zeros((n_Re)),                      desc='Grid of the Reynolds numbers used to define the polars of the airfoils. All airfoils defined in openmdao share this grid.')
        self.add_input('af_tab', val=np.zeros((n_tab)),                     desc='Grid of the values of the "tab" entity used to define the polars of the airfoils. All airfoils defined in openmdao share this grid. The tab could for example represent a flap deflection angle.')
        self.add_input('af_cl',  val=np.zeros((n_af, n_aoa, n_Re, n_tab)),  desc='4 dimensional array with the lift coefficients of the airfoils. Dimension 0 is aling the different airfoils defined in the yaml, dimension 1 is along the angles of attack, dimension 2 is along the Reynolds number, dimension 3 is along the number of tabs, which may describe multiple sets at the same station, for example in presence of a flap.')
        self.add_input('af_cd',  val=np.zeros((n_af, n_aoa, n_Re, n_tab)),  desc='4 dimensional array with the drag coefficients of the airfoils. Dimension 0 is aling the different airfoils defined in the yaml, dimension 1 is along the angles of attack, dimension 2 is along the Reynolds number, dimension 3 is along the number of tabs, which may describe multiple sets at the same station, for example in presence of a flap.')
        self.add_input('af_cm',  val=np.zeros((n_af, n_aoa, n_Re, n_tab)),  desc='4 dimensional array with the moment coefficients of the airfoils. Dimension 0 is aling the different airfoils defined in the yaml, dimension 1 is along the angles of attack, dimension 2 is along the Reynolds number, dimension 3 is along the number of tabs, which may describe multiple sets at the same station, for example in presence of a flap.')
        
        # Airfoil coordinates
        self.add_input('af_coord_x',  val=np.zeros((n_af, n_xy)),           desc='Array of the x airfoil coordinates of the n_af airfoils.')
        self.add_input('af_coord_y',  val=np.zeros((n_af, n_xy)),           desc='Array of the y airfoil coordinates of the n_af airfoils.')
        
        

class WT_Data(Group):
    # Openmdao group with all wind turbine data
    
    def initialize(self):
        self.options.declare('wt_init_options')
        
    def setup(self):
        wt_init_options = self.options['wt_init_options']
        self.add_subsystem('materials', Materials(mat_init_options = wt_init_options['materials']))
        self.add_subsystem('airfoils',  Airfoils(af_init_options   = wt_init_options['airfoils']))

def yaml2openmdao(wt_opt, wt_init_options, blade, tower, nacelle, materials, airfoils):
    # Function to assign values to the openmdao group WT_Data and all its components
    
    wt_opt = assign_material_values(wt_opt, wt_init_options, materials)
    wt_opt = assign_airfoils_values(wt_opt, wt_init_options, airfoils)
    
    return wt_opt
    
def assign_material_values(wt_opt, wt_init_options, materials):
    # Function to assign values to the openmdao component Materials
    
    n_mat = wt_init_options['materials']['n_mat']
    
    name        = n_mat * ['']
    orth        = np.zeros(n_mat)
    component_id= -np.ones(n_mat)
    rho         = np.zeros(n_mat)
    E           = np.zeros([n_mat, 3])
    G           = np.zeros([n_mat, 3])
    nu          = np.zeros([n_mat, 3])
    rho_fiber   = np.zeros(n_mat)
    rho_area_dry= np.zeros(n_mat)
    fvf         = np.zeros(n_mat)
    fvf         = np.zeros(n_mat)
    fwf         = np.zeros(n_mat)
    
    for i in range(n_mat):
        name[i] =  materials[i]['name']
        orth[i] =  materials[i]['orth']
        rho[i]  =  materials[i]['rho']
        if 'component_id' in materials[i]:
            component_id[i] = materials[i]['component_id']
        
        if orth[i] == 0:
            if 'E' in materials[i]:
                E[i,:]  = np.ones(3) * materials[i]['E']
            if 'nu' in materials[i]:
                nu[i,:] = np.ones(3) * materials[i]['nu']
            if 'G' in materials[i]:
                G[i,:]  = np.ones(3) * materials[i]['G']
            elif 'nu' in materials[i]:
                G[i,:]  = np.ones(3) * materials[i]['E']/(2*(1+materials[i]['nu'])) # If G is not provided but the material is isotropic and we have E and nu we can just estimate it
                warning_shear_modulus_isotropic = 'Ontology input warning: No shear modulus, G, provided for material "%s".  Assuming 2G*(1 + nu) = E, which is only valid for isotropic materials.'%mati['name']
                print(warning_shear_modulus_isotropic)
                
        elif orth[i] == 1:
            E[i,:]  = materials[i]['E']
            G[i,:]  = materials[i]['G']
            nu[i,:] = materials[i]['nu']
        else:
            exit('')
        if 'fiber_density' in materials[i]:
            rho_fiber[i]    = materials[i]['fiber_density']
        if 'area_density_dry' in materials[i]:
            rho_area_dry[i] = materials[i]['area_density_dry']
        
        
        if 'fvf' in materials[i]:
            fvf[i] = materials[i]['fvf']
        if 'fwf' in materials[i]:
            fwf[i] = materials[i]['fwf']
            
            
    wt_opt['materials.name']     = name
    wt_opt['materials.orth']     = orth
    wt_opt['materials.rho']      = rho
    wt_opt['materials.component_id']= component_id
    wt_opt['materials.E']        = E
    wt_opt['materials.G']        = G
    wt_opt['materials.nu']       = nu
    wt_opt['materials.rho_fiber']      = rho_fiber
    wt_opt['materials.rho_area_dry']   = rho_area_dry
    wt_opt['materials.fvf']      = fvf
    wt_opt['materials.fwf']      = fwf

    return wt_opt

def assign_airfoils_values(wt_opt, wt_init_options, airfoils):
    # Function to assign values to the openmdao component Airfoils
    
    n_af  = wt_init_options['airfoils']['n_af']
    n_aoa = wt_init_options['airfoils']['n_aoa']
    n_Re  = wt_init_options['airfoils']['n_Re']
    n_tab = wt_init_options['airfoils']['n_tab']
    n_xy  = wt_init_options['airfoils']['n_xy']

     
    return wt_opt
    
    
    
    
if __name__ == "__main__":

    ## File management
    # fname_input        = "turbine_inputs/nrel5mw_mod_update.yaml"
    fname_input        = "/mnt/c/Material/Projects/Hitachi_Design/Design/turbine_inputs/aerospan_formatted_v13.yaml"
    fname_output       = "turbine_inputs/testing_twist.yaml"
    
    wt_initial              = Wind_Turbine()
    wt_initial.validate     = False
    wt_initial.fname_schema = "turbine_inputs/IEAontology_schema.yaml"
    wt_init_options, blade, tower, nacelle, materials, airfoils = wt_initial.initialize(fname_input)
    
    wt_opt          = Problem()
    wt_opt.model    = WT_Data(wt_init_options = wt_init_options)
    wt_opt.setup()
    wt_opt = yaml2openmdao(wt_opt, wt_init_options, blade, tower, nacelle, materials, airfoils)
    wt_opt.run_driver()
    
    


















