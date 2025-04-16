import matplotlib.pyplot as plt
import epics

def bdesToKmod(element, BDES, tao):
    val = tao.cmd(f'show lat -attr E_TOT {element} -no_label_lines')
    elementEnergy = float(val[0].split()[-1]) / 1E9
    val = tao.cmd(f'show lat -attr L {element} -no_label_lines')
    elementLeff = float(val[0].split()[-1]) #m
    bp = elementEnergy  / 299.792458*1e4;#  kG m
    return BDES / elementLeff / bp #kG / m / kG m = 1/m^2

def bdes_to_kmod(element, tao, BDES):
    element_energy = tao.ele_gen_attribs(element)['E_TOT']/1E9
    element_leff =  tao.ele_gen_attribs(element)['L']
    bp = element_energy  / 299.792458*1e4;#kG m
    return BDES / element_leff / bp #1/m^2

def kmod_to_bdes(element, tao, K1 = 0):
    ele_attribs =  tao.ele_gen_attribs(element)
    if K1 == 0:
        K1 = ele_attribs['K1']
    element_energy = ele_attribs['E_TOT']/1E9
    element_leff =  ele_attribs['L']
    bp = element_energy / 299.792458*1e4;#kG m
    return K1 * bp * element_leff 




def get_pvlist(ALL_DATAMAPS):
    pvlist = set()
    for dm_key in ALL_DATAMAPS.keys():
        for pv in ALL_DATAMAPS[dm_key].pvlist:
            pvlist.add(pv) 
    return list(pvlist)

def get_bmad(pvdata):
    lines = []
    for dm in ALL_DATAMAPS:
        lines += dm.as_bmad(pvdata)
    return lines

def get_tao(pvdata, ALL_DATAMAPS):
    lines = []
    for dm_key in ALL_DATAMAPS.keys():
        lines +=  ALL_DATAMAPS[dm_key].as_tao(pvdata)
    return lines

def get_tao_dm(pvdata, DATAMAP):
    lines = []
    lines += DATAMAP.as_tao(pvdata)
    return lines


def get_live(pvlist):
    return dict(zip(pvlist, epics.caget_many(pvlist)))

def get_pvlist_rf(ALL_DATAMAPS):
    pvlist_rf = set()
    pvlist_magnets_linac = set()
    pvlist_magnets_ltu = set()
    isLinac = True
    for dm_key in ALL_DATAMAPS.keys():
        dm = ALL_DATAMAPS[dm_key]
        for pv in dm.pvlist:
            if pv.startswith(('SBST','ACCL','KLYS')):
                pvlist_rf.add(pv) 
            elif pv.endswith('EDES'): 
                #if pv.startswith('BEND:DMPS')):
                #    continue
                pvlist_rf.add(pv)
            else:
                if isLinac:
                    pvlist_magnets_linac.add(pv)
                else:
                    pvlist_magnets_ltu.add(pv)
                if pv == 'QUAD:CLTH:170:BDES':
                    isLinac = False
    return (list(pvlist_rf), list(pvlist_magnets_linac), list(pvlist_magnets_ltu))



def evaluate_tao(tao, init_cmds, cmds, final_cmds):
    # Init
    for cmd in init_cmds:
        tao.cmd(cmd)
    for cmd in cmds:
        tao.cmd(cmd)
    # Turn lattice calc on
    for cmd in final_cmds:
        tao.cmd(cmd)    
    output = get_output(tao)
    return output

def make_cmds(cmd_string):
    s = cmd_string.split('\n')
    return list(filter(None,s))


def tc(tao, cmd):
    result = tao.cmd(cmd)
    for l in result:
        print(l)


def getEtot(element):
    result = tao.cmd(f'show lat {element} -attr p0c -no_label_lines')
    print(result)
    return float(result[0].split()[-1]) / 1e9

def print_twiss(tao, element, datum=[]):
    result_model = tao.ele_twiss(element,which='model')
    result_design = tao.ele_twiss(element,which='design')
    if not datum == []:
        result_datum = tao.data_parameter(datum, 'meas_value')[0].split(';')[1:]
    parameters = ['beta_a', 'alpha_a', 'beta_b', 'alpha_b']
    twiss_model = [result_model[p] for p in parameters]
    twiss_design = [result_design[p] for p in parameters]
    bmag_a, bmag_b = calc_bmag(twiss_model, twiss_design)
    print(f'\n{element} BMAG_X {bmag_a:3.2f}, BMAG_Y {bmag_b:3.2f} ')
    print(f'{" " * 12} Beta     Alpha   Beta   Alpha ')
    print(f'{" " * 12}  X       X       Y       Y')
    print(f'Desing:{" "} ', end='')
    r = [print(f'{result_design[par]:8.2f}', end='') for par in  parameters]
    print('')
    print(f'Model:{" " *3}', end='')
    r = [print(f'{result_model[par]:8.2f}', end='') for par in  parameters]
    print('')
    if not datum == []:
        print(f'Measured:{" " * 0}', end='')
        r = [print(f'{float(result_datum[ii]):8.2f}', end='') for ii,par in  enumerate(parameters)]
        print('')
    
def bmag(bb,ab,bl,al):
    return 1/2 * (bl/bb + bb/bl + bb*bl*(ab/bb - al/bl)**2)

def calc_bmag(twiss_model, twiss_desing):
    beta_a, alpha_a, beta_b, alpha_b = twiss_model
    beta_a_design,  alpha_a_design, beta_b_design, alpha_b_design = twiss_desing
    bmag_a = bmag(beta_a, alpha_a, beta_a_design, alpha_a_design)
    bmag_b = bmag(beta_b, alpha_b, beta_b_design, alpha_b_design)
    return (bmag_a, bmag_b)


def view(str):
    for l in str:
        print(l)

fudge_L1_cmds = [
'veto dat * ',  
'veto var *',
'use dat BC1.energy[1]',
'use var linac_fudge[1]',
'run']

fudge_L2_cmds =[
'veto dat *',   
'veto var *',
'use dat BC2.energy[1]',
'use var linac_fudge[2]',
'run']

fudge_L3_cmds = [
'veto dat *',  
'veto var *',
'use dat L3.energy[2]',
'use var linac_fudge[3]',
'run']



# Output collecting
outkeys = [
'ele.name',
'ele.ix_ele',
'ele.ix_branch',
'ele.a.beta',
'ele.a.alpha',
'ele.a.eta',
'ele.a.etap',
'ele.a.gamma',
'ele.a.phi',
'ele.b.beta',
'ele.b.alpha',
'ele.b.eta',
'ele.b.etap',
'ele.b.gamma',
'ele.b.phi',
'ele.x.eta',
'ele.x.etap',
'ele.y.eta',
'ele.y.etap',
'ele.s',
'ele.l',
'ele.e_tot',
'ele.p0c',
'ele.mat6',
'ele.vec0']

showemit = [
'show data emitmeas.OTR2[1:4]'
'show data emitmeas.LI21[1:4]' 
'show data emitmeas.LI28[1:4]'   
'show data emitmeas.LTU[1:4]' ] 

def get_output(tao):
    return {k:tao.lat_list('*', k) for k in outkeys}

def plot_twiss(tao, output, info='', xoff = 0):
    fig, ax = plt.subplots(figsize=(8,4))
    ax.plot(output['ele.s'], output['ele.a.beta'], label = r'$\beta_a$')
    ax.plot(output['ele.s'], output['ele.b.beta'], label = r'$\beta_b$')
    plt.legend()
    # Add energy to the rhs
    ax2 = ax.twinx()
    ax2.plot(output['ele.s'], output['ele.e_tot']/1e9, color='red')
    ax2.set_ylabel('Energy (GeV)')
    ax.set_xlabel('s (m)')
    ax.set_ylabel('Twiss Beta (m)')
    #itime = isotime()
    efinal = output['ele.e_tot'][-1]/1e9
    plt.title(f'{info} Final energy: {efinal:.2f} GeV')
    quads = tao.lat_list('quad::Q*','ele.name',flags='-no_slaves')
    for q in quads:
        plt.text(tao.ele_head(q)['s'], -30, q, rotation=90, ha='center', va='center',fontsize=8, transform=ax.transData)
    return fig

def plot_betas(output1, output2, info='', plane=''):
    fig1, ax1 = plt.subplots(figsize=(8,4))
    ax1.plot(output1['ele.s'], output1['ele.a.beta'], label = r'$Design$', linestyle = '--')
    ax1.plot(output2['ele.s'], output2['ele.a.beta'], label = r'$Model$')
    plt.legend()
    # Add energy to the rhs
    ax12 = ax1.twinx()
    ax12.plot(output2['ele.s'], output2['ele.e_tot']/1e9, color='red')
    ax12.set_ylabel('Energy (GeV)')
    efinal = output2['ele.e_tot'][-1]/1e9
    plt.title(f'{info} Final energy: {efinal:.2f} GeV')
    ax1.set_xlabel('s (m)')
    ax1.set_ylabel('Twiss Beta X (m)')
    #itime = isotime()
    fig2, ax2 = plt.subplots(figsize=(8,4))    
    ax2.plot(output1['ele.s'], output1['ele.b.beta'], label = r'$Design$', linestyle = '--')
    ax2.plot(output2['ele.s'], output2['ele.b.beta'], label = r'$Model$')
    plt.legend()
    ax22 = ax2.twinx()
    ax22.plot(output2['ele.s'], output2['ele.e_tot']/1e9, color='red')
    ax22.set_ylabel('Energy (GeV)')
    plt.title(f'{info} Final energy: {efinal:.2f} GeV')
    ax2.set_xlabel('s (m)')
    ax2.set_ylabel('Twiss Beta Y (m)')
    axes_list = [ax1, ax12, ax2, ax22]
    return fig1, fig2, axes_list



def plot_dispersion(output, info=''):
    fig, ax = plt.subplots(figsize=(8,4))
    ax.plot(output['ele.s'], output['ele.x.eta']*1000, label = r'$\eta_x$')
    ax.plot(output['ele.s'], output['ele.y.eta']*1000, label = r'$\eta_y$')
    plt.legend()
    ax.set_xlabel('s (m)')
    ax.set_ylabel('Eta (mm)')
    ax.grid(True)
    return fig



def get_quad_bdes(tao):
    #quad_names = tao.lat_list('quad::Q*','ele.name',flags='-no_slaves')
    quad_lat_list = tao.cmd('python show lat -attr b1_gradient  Quad::* -no_slaves -no_label_lines')
    quad_bdes = {}
    for line in quad_lat_list:
        (index, quad, key, s, length, gradient) = line.split()
        g = float(gradient)
        l = float(length)
        quad_bdes[quad] = -g * l * 10
    return quad_bdes





use_LI21 = [
'use dat emitmeas.LI21',
'set dat emitmeas.LI21|meas = emitmeas.LI21|design']

use_BC2 = [ 
'use dat BC2.begtwiss',
'set dat BC2.begtwiss|meas = BC2.begtwiss|design']

use_BEGL3 = [
'use dat BEGL3.match_twiss[1:4]',
'set dat BEGL3.match_twiss|meas = BEGL3.match_twiss|design']

use_LI28 =[
'use dat emitmeas.LI28',
'set dat emitmeas.LI28|meas = emitmeas.LI28|design']

use_LTUH_M = [
'use dat LTUH_M.match_twiss[1:4]',
'set dat LTUH_M.match_twiss|meas = LTUH_M.match_twiss|design']
                              
match_init_cmds = [
'veto var *',
'veto dat *@*',
'set global n_opti_cycles = 912']

match_final_cmds = [
'use var begtwiss[1:4]',
'run']

init_cmds =['set global lattice_calc_on = F']
final_cmds =['set global lattice_calc_on = T']


