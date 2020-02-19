import numpy as np

elemlist = ['h', 'he', 'c', 'o', 'ne', 'na', 'mg', 'al', 'si', 's',
            'k', 'ca', 'cr', 'fe', 'ni']

CROSTAB_LIST = ['h_' + clist for clist in elemlist]
CROSTAB_LIST += ['e_' + clist for clist in elemlist]
for iel in elemlist:
    CROSTAB_LIST = CROSTAB_LIST + [
        iel + '_' + clist for clist in elemlist]

def load_quantities(obj,quant, *args, PLASMA_QUANT=None, CYCL_RES=None,
                COLFRE_QUANT=None, COLFRI_QUANT=None, IONP_QUANT=None,
                EOSTAB_QUANT=None, TAU_QUANT=None, DEBYE_LN_QUANT=None,
                CROSTAB_QUANT=None, COULOMB_COL_QUANT=None, AMB_QUANT=None,
                HALL_QUANT=None, **kwargs):
    quant = quant.lower()

    if not hasattr(obj,'description'):
        obj.description = {}

    val = get_coulomb(obj,quant)
    if np.shape(val) is ():
        val = get_collision(obj,quant)
    if np.shape(val) is ():
        val = get_crossections(obj,quant)
    if np.shape(val) is ():
        val = get_collision_ms(obj,quant)
    if np.shape(val) is ():
        val = get_current(obj,quant)
    if np.shape(val) is ():
        val = get_flux(obj,quant)
    if np.shape(val) is ():
        val = get_plasmaparam(obj,quant)
    if np.shape(val) is ():
        val = get_wavemode(obj,quant)
    if np.shape(val) is ():
        val = get_cyclo_res(obj,quant)
    if np.shape(val) is ():
        val = get_gyrof(obj,quant)
    if np.shape(val) is ():
        val = get_kappa(obj,quant)
    if np.shape(val) is ():
        val = get_debye_ln(obj,quant)
    if np.shape(val) is ():
        val = get_ionpopulations(obj,quant)
    if np.shape(val) is ():
        val = get_ambparam(obj,quant)
    if np.shape(val) is ():
        val = get_hallparam(obj,quant)
    return val

def get_crossections(obj, quant, CROSTAB_QUANT=None):

    if CROSTAB_QUANT is None:
        CROSTAB_QUANT = CROSTAB_LIST
    obj.description['CROSTAB'] = ('Cross section between species'
        '(in cgs): ' + ', '.join(CROSTAB_QUANT))
    obj.description['ALL'] += "\n"+ obj.description['CROSTAB']

    if (quant == ''):
        return None

    if quant in CROSTAB_QUANT:
        tg = obj.get_var('tg')
        elem = quant.split('_')

        spic1 = ''.join([i for i in elem[0] if not i.isdigit()])
        spic2 = ''.join([i for i in elem[1] if not i.isdigit()])

        cross_tab = ''
        crossunits = 2.8e-17

        if ([spic1,spic2] == ['h','h']) :
            cross_tab = 'p-h-elast.txt'
        elif (([spic1,spic2] == ['h','he']) or ([spic2,spic1] == ['h','he'])):
            cross_tab = 'p-he.txt'
        elif ([spic1,spic2] == ['he','he']):
            cross_tab = 'he-he.txt'
            crossunits = 1e-16
        elif (([spic1,spic2] == ['e','he']) or ([spic2,spic1] == ['e','he'])):
            cross_tab = 'e-he.txt'
            crossunits = 1e-16
        elif (([spic1,spic2]==['e','h']) or ([spic2,spic1]==['e','h'])):
            cross_tab = 'e-h.txt'
            crossunits = 1e-16
        elif (spic1 == 'h'):
            cross = obj.uni.weightdic[spic2] / obj.uni.weightdic['h'] * \
                obj.uni.cross_p * np.ones(np.shape(tg))
        elif (spic2 == 'h'):
            cross = obj.uni.weightdic[spic1] / obj.uni.weightdic['h'] * \
                obj.uni.cross_p * np.ones(np.shape(tg))
        elif (spic1 == 'he'):
            cross = obj.uni.weightdic[spic2] / obj.uni.weightdic['he'] * \
                obj.uni.cross_he * np.ones(np.shape(tg))
        elif (spic2 == 'he'):
            cross = obj.uni.weightdic[spic1] / obj.uni.weightdic['he'] * \
                obj.uni.cross_he * np.ones(np.shape(tg))

        if cross_tab != '':
            crossobj = obj.cross_sect(cross_tab=[cross_tab])
            cross = crossunits * crossobj.tab_interp(tg)

        try:
            return cross
        except Exception:
            print('(WWW) cross-section: wrong combination of species')
    else:
        return None

def get_collision(obj,quant, COLFRE_QUANT=None):

    if COLFRE_QUANT is None:
        COLFRE_QUANT = ['nu' + clist for clist in CROSTAB_LIST]
        COLFRE_QUANT += ['nu%s_mag'% clist for clist in CROSTAB_LIST]
        COLFRE_QUANT += ['nue_'+ clist for clist in elemlist]
        obj.description['COLFRE'] = ('Collision frequency (elastic and charge'
            'exchange) between different species in (cgs): ' +
            ', '.join(COLFRE_QUANT))
        obj.description['ALL'] += "\n"+ obj.description['COLFRE']

    if (quant == ''):
        return None

    if ''.join([i for i in quant if not i.isdigit()]) in COLFRE_QUANT:

        elem = quant.split('_')
        spic1 = ''.join([i for i in elem[0] if not i.isdigit()])
        ion1 = ''.join([i for i in elem[0] if i.isdigit()])
        spic2 = ''.join([i for i in elem[1] if not i.isdigit()])
        ion2 = ''.join([i for i in elem[1] if i.isdigit()])

        spic1 = spic1[2:]
        crossarr = obj.get_var('%s_%s' % (spic1, spic2))
        nspic2 = obj.get_var('n%s-%s' % (spic2, ion2))
        if np.size(elem) > 2:
            nspic2 *= (1.0-obj.get_var('kappanorm_%s'%spic2))

        tg = obj.get_var('tg')
        if spic1 == 'e':
            awg1 = obj.uni.m_electron
        else:
            awg1 = obj.uni.weightdic[spic1] * obj.uni.amu
        if spic1 == 'e':
            awg2 = obj.uni.m_electron
        else:
            awg2 = obj.uni.weightdic[spic2] * obj.uni.amu
        scr1 = np.sqrt(8.0 * obj.uni.kboltzmann * tg / obj.uni.pi)

        return crossarr * np.sqrt((awg1 + awg2) / (awg1 * awg2)) *\
            scr1 * nspic2 #* (awg1 / (awg1 + awg1))
    else:
        return None

def get_collision_ms(obj,quant, COLFRI_QUANT=None):

    if (COLFRI_QUANT == None):
        COLFRI_QUANT = ['nu_ni', 'nu_en', 'nu_ei', 'nu_in', 'nu_nis', 'nu_ins']
        COLFRI_QUANT += ['nu_ni_mag', 'nu_in_mag', 'nu_nis_mag', 'nu_ins_mag']
        COLFRI_QUANT = COLFRI_QUANT + \
            ['nu' + clist + '_i' for clist in elemlist]
        COLFRI_QUANT = COLFRI_QUANT + \
            ['nu' + clist + '_n' for clist in elemlist]
        COLFRI_QUANT = COLFRI_QUANT + \
            ['nu' + clist + '_is' for clist in elemlist]
        COLFRI_QUANT = COLFRI_QUANT + \
            ['nu' + clist + '_is_mag' for clist in elemlist]
        COLFRI_QUANT = COLFRI_QUANT + \
            ['nu' + clist + '_ns' for clist in elemlist]
        COLFRI_QUANT = COLFRI_QUANT + \
            ['nu' + clist + '_ns_mag' for clist in elemlist]
        obj.description['COLFRI'] = ('Collision frequency (elastic and charge'
            'exchange) between fluids in (cgs): ' + ', '.join(COLFRI_QUANT))
        obj.description['ALL'] += "\n"+ obj.description['COLFRI']

    if (quant == ''):
        return None

    if ''.join([i for i in quant if not i.isdigit()]) in COLFRI_QUANT:
        if quant == 'nu_ni':
            result = obj.uni.m_h * obj.get_var('nh-1') * \
                obj.get_var('nuh1_i') + \
                obj.uni.m_he * obj.get_var('nhe-1') * obj.get_var('nuhe1_i')

        if quant == 'nu_in':
            result = np.zeros(np.shape(obj.r))
            for ielem in elemlist:
                result += obj.uni.amu * obj.uni.weightdic[ielem] * obj.get_var('n%s-2'%ielem) * \
                    obj.get_var('nu%s2_n'%ielem)
            if obj.heion:
                result += obj.uni.amu * obj.uni.weightdic['he'] * obj.get_var('nhe3') * \
                    obj.get_var('nuhe3_n')

        if quant == 'nu_nis':
            result = obj.uni.m_h * obj.get_var('nh-1') * \
                obj.get_var('nuh1_is') + \
                obj.uni.m_he * obj.get_var('nhe-1') * obj.get_var('nuhe1_is')
            #for ielem in elemlist[2:]:
            #    result +=  obj.get_var('r%s-1')%ielem * obj.get_var('nu%s1_is')%ielem

        if quant == 'nu_nis_mag':
            result = obj.uni.m_h * obj.get_var('nh-1') * \
                obj.get_var('nuh1_is_mag') + \
                obj.uni.m_he * obj.get_var('nhe-1') * obj.get_var('nuhe1_is_mag')
            #for ielem in elemlist[2:]:
            #    result +=  obj.get_var('r%s-1'%ielem) * \
            #        obj.get_var('kappanorm_%s'%ielem) * obj.get_var('nu%s1_is_mag'%ielem)

        if quant == 'nu_ins':
            result = obj.uni.m_h * obj.get_var('nh-2') * \
                obj.get_var('nuh2_ns') + \
                obj.uni.m_he * obj.get_var('nhe-2') * obj.get_var('nuhe2_ns') + \
                obj.uni.m_he * obj.get_var('nhe-3') * obj.get_var('nuhe3_ns')
            #for ielem in elemlist[2:]:
            #    result +=  obj.get_var('r%s-2')%ielem * obj.get_var('nu%s2_ns')%ielem

        if quant == 'nu_ins_mag':
            result = obj.uni.m_h * obj.get_var('nh-2') * \
                obj.get_var('nuh2_ns') + \
                obj.uni.m_he * obj.get_var('nhe-2') * obj.get_var('nuhe2_ns_mag') + \
                obj.uni.m_he * obj.get_var('nhe-3') * obj.get_var('nuhe3_ns_mag')
            #for ielem in elemlist[2:]:
            #    result +=  obj.get_var('r%s-2')%ielem * \
            #        obj.get_var('kappanorm_%s'%ielem) * obj.get_var('nu%s2_ns_mag')%ielem

        elif quant == 'nu_ei':
            if obj.hion:
                nel = obj.get_var('hionne')
            else:
                nel = obj.get_var('nel')
            culblog = 23. + 1.5 * np.log(obj.get_var('tg') / 1.e6) - \
                0.5 * np.log(nel / 1e6)

            result = 3.759 * nel / (obj.get_var('tg')**(1.5)) * culblog

        elif quant == 'nu_en':
            elem = quant.split('_')
            result = np.zeros(np.shape(obj.r))
            lvl = 1
            for ielem in elemlist:
                if ielem in ['h','he']:
                    result += obj.get_var('%s_%s%s' %
                                   ('nue', ielem, lvl))
            #if obj.hion:
            #    nel = obj.get_var('hionne')
            #else:
            #    nel = obj.get_var('nel')
            #culblog = 23. + 1.5 * np.log(obj.get_var('tg') / 1.e6) - \
            #    0.5 * np.log(nel / 1e6)
            #scr1 = 3.759 * nel / (obj.get_var('tg')**(1.5)) * culblog
            #scr2 = 0.0 * nel
            #for ielem in elemlist:
            #    scr2 += obj.get_var('n%s-%s' % (ielem, 1)
            #result = 5.2e-11 * scr2 / nel * obj.get_var('tg')**2 / \
            #    culblog * scr1
            #for ielem in elemlist:
            #    result+=obj.uni.amu * obj.uni.weightdic[ielem] * obj.get_var('n%s-2'%ielem) * \
            #        obj.get_var('nu%s2_n'%ielem)

        elif quant[-2:] == '_i' or quant[-2:] == '_n':
            if quant[-2:] == '_i':
                lvl = '2'
            else:
                lvl = '1'
            elem = quant.split('_')
            result = np.zeros(np.shape(obj.r))
            for ielem in elemlist:
                if elem[0][2:] in ['h','he'] or ielem in ['h','he']:
                    if elem[0][2:] != '%s%s' % (ielem, lvl):
                        result += obj.get_var('%s_%s%s' %
                                           (elem[0], ielem, lvl))
            if obj.heion and quant[-2:] == '_i':
                result += obj.get_var('%s_%s' % (elem[0], 'he3'))

        elif (('_is' in quant) or ('_ns' in quant)):
            addtxt = ''
            if quant[-4:] == '_mag':
                addtxt = '_mag'
            if '_is' in quant:
                lvl = '2'
            else:
                lvl = '1'
            elem = quant.split('_')
            result = np.zeros(np.shape(obj.r))
            for ielem in elemlist:
                if elem[0][2:] != '%s%s' % (ielem, lvl):
                    result += obj.get_var('%s_%s%s%s' %
                            (elem[0], ielem, lvl, addtxt)) * obj.uni.weightdic[ielem] /\
                            (obj.uni.weightdic[ielem] + obj.uni.weightdic[elem[0][2:-1]])
            if obj.heion and quant[-3:] == '_is':
                result += obj.get_var('%s_%s%s' % (elem[0], 'he3', addtxt)) * obj.uni.weightdic['he'] /\
                        (obj.uni.weightdic['he'] + obj.uni.weightdic[elem[0][2:-1]])

        return result
    else:
        return None

def get_coulomb(obj, quant, COULOMB_COL_QUANT=None):

    if COULOMB_COL_QUANT is None:
        COULOMB_COL_QUANT = ['coucol' + clist for clist in elemlist]
        obj.description['COULOMB_COL'] = ('Coulomb collision frequency in Hz'
            'units: ' + ', '.join(COULOMB_COL_QUANT))
        if 'ALL' in obj.description.keys():
            obj.description['ALL'] += "\n"+ obj.description['COULOMB_COL']
        else:
            obj.description['ALL'] = "\n"+ obj.description['COULOMB_COL']

    if (quant == ''):
        return None

    if quant in COULOMB_COL_QUANT:
        iele = np.where(COULOMB_COL_QUANT == quant)
        tg = obj.get_var('tg')
        nel = np.copy(obj.get_var('ne'))
        elem = quant.replace('coucol', '')

        const = (obj.uni.pi * obj.uni.qsi_electron ** 4 /
                 ((4.0 * obj.uni.pi * obj.uni.permsi)**2 *
                  np.sqrt(obj.uni.weightdic[elem] * obj.uni.amusi *
                         (2.0 * obj.uni.ksi_b) ** 3) + 1.0e-20))

        return (const * nel.astype('Float64') *
                np.log(12.0 * obj.uni.pi * nel.astype('Float64') *
                obj.get_var('debye_ln').astype('Float64') + 1e-50) /
                (np.sqrt(tg.astype('Float64')**3) + 1.0e-20))
    else:
        return None

def get_current(obj, quant, CURRENT_QUANT=None):

    if CURRENT_QUANT is None:
        CURRENT_QUANT = ['ix', 'iy', 'iz', 'wx', 'wy', 'wz']
        obj.description['CURRENT'] = ('Calculates currents (bifrost units) or'
            'rotational components of the velocity as follows ' +
            ', '.join(CURRENT_QUANT))
        obj.description['ALL'] += "\n"+ obj.description['CURRENT']

    if (quant == ''):
        return None

    if quant in CURRENT_QUANT:
        # Calculate derivative of quantity
        axis = quant[-1]
        if quant[0] == 'i':
            q = 'b'
        else:
            q = 'u'
        try:
            var = getattr(obj, quant)
        except AttributeError:
            if axis == 'x':
                varsn = ['z', 'y']
                derv = ['dydn', 'dzdn']
            elif axis == 'y':
                varsn = ['x', 'z']
                derv = ['dzdn', 'dxdn']
            elif axis == 'z':
                varsn = ['y', 'x']
                derv = ['dxdn', 'dydn']

            # 2D or close
            if (getattr(obj, 'n' + varsn[0]) < 5) or (getattr(obj, 'n' + varsn[1]) < 5):
                return np.zeros_like(obj.r)
            else:
                return (obj.get_var('d' + q + varsn[0] + derv[0]) -
                        obj.get_var('d' + q + varsn[1] + derv[1]))

    else:
        return None



def get_flux(obj, quant, FLUX_QUANT=None):

    if FLUX_QUANT is None:
        FLUX_QUANT = ['pfx', 'pfy', 'pfz', 'pfex', 'pfey', 'pfez', 'pfwx',
                    'pfwy', 'pfwz']
    obj.description['FLUX'] = ('Poynting flux, Flux emergence, and'
        'Poynting flux from "horizontal" motions: ' +
        ', '.join(FLUX_QUANT))
    obj.description['ALL'] += "\n"+ obj.description['FLUX']

    if (quant == ''):
        return None

    if quant in FLUX_QUANT:
        axis = quant[-1]
        if axis == 'x':
            varsn = ['z', 'y']
        elif axis == 'y':
            varsn = ['x', 'z']
        elif axis == 'z':
            varsn = ['y', 'x']
        if 'pfw' in quant or len(quant) == 3:
            var = - obj.get_var('b' + axis + 'c') * (
                obj.get_var('u' + varsn[0] + 'c') *
                obj.get_var('b' + varsn[0] + 'c') +
                obj.get_var('u' + varsn[1] + 'c') *
                obj.get_var('b' + varsn[1] + 'c'))
        else:
            var = np.zeros_like(obj.r)
        if 'pfe' in quant or len(quant) == 3:
            var += obj.get_var('u' + axis + 'c') * (
                obj.get_var('b' + varsn[0] + 'c')**2 +
                obj.get_var('b' + varsn[1] + 'c')**2)
        return var
    else:
        return None



def get_plasmaparam(obj, quant, PLASMA_QUANT=None):

    if PLASMA_QUANT is None:
        PLASMA_QUANT = ['beta', 'va', 'cs', 's', 'ke', 'mn', 'man', 'hp',
                    'vax', 'vay', 'vaz', 'hx', 'hy', 'hz', 'kx', 'ky',
                    'kz']
        obj.description['PLASMA'] = ('Plasma beta, alfven velocity (and its'
            'components), sound speed, entropy, kinetic energy flux'
            '(and its components), magnetic and sonic Mach number'
            'pressure scale height, and each component of the total energy'
            'flux (if applicable, Bifrost units): ' +
            ', '.join(PLASMA_QUANT))
        obj.description['ALL'] += "\n"+ obj.description['PLASMA']

    if (quant == ''):
        return None

    if quant in PLASMA_QUANT:
        if quant in ['hp', 's', 'cs', 'beta']:
            var = obj.get_var('p')
            if quant == 'hp':
                if getattr(obj, 'nx') < 5:
                    return np.zeros_like(var)
                else:
                    return 1. / (cstagger.do(var, 'ddzup') + 1e-12)
            elif quant == 'cs':
                return np.sqrt(obj.params['gamma'][obj.snapInd] *
                               var / obj.get_var('r'))
            elif quant == 's':
                return (np.log(var) - obj.params['gamma'][obj.snapInd] *
                        np.log(obj.get_var('r')))
            elif quant == 'beta':
                return 2 * var / obj.get_var('b2')

        if quant in ['mn', 'man']:
            var = obj.get_var('modu')
            if quant == 'mn':
                return var / (obj.get_var('cs') + 1e-12)
            else:
                return var / (obj.get_var('va') + 1e-12)

        if quant in ['va', 'vax', 'vay', 'vaz']:
            var = obj.get_var('r')
            if len(quant) == 2:
                return obj.get_var('modb') / np.sqrt(var)
            else:
                axis = quant[-1]
                return np.sqrt(obj.get_var('b' + axis + 'c') ** 2 / var)

        if quant in ['hx', 'hy', 'hz', 'kx', 'ky', 'kz']:
            axis = quant[-1]
            var = obj.get_var('p' + axis + 'c')
            if quant[0] == 'h':
                return ((obj.get_var('e') + obj.get_var('p')) /
                         obj.get_var('r') * var)
            else:
                return obj.get_var('u2') * var * 0.5

        if quant in ['ke']:
            var = obj.get_var('r')
            return obj.get_var('u2') * var * 0.5
    else:
        return None


def get_wavemode(obj, quant, WAVE_QUANT=None):

    if WAVE_QUANT is None:
        WAVE_QUANT = ['alf', 'fast', 'long']
        obj.description['WAVE'] = ('Alfven, fast and longitudinal wave'
            'components (Bifrost units): ' + ', '.join(WAVE_QUANT))
        obj.description['ALL'] += "\n"+ obj.description['WAVE']

    if (quant == ''):
        return None

    if quant in WAVE_QUANT:
        bx = obj.get_var('bxc')
        by = obj.get_var('byc')
        bz = obj.get_var('bzc')
        bMag = np.sqrt(bx**2 + by**2 + bz**2)
        bx, by, bz = bx / bMag, by / bMag, bz / bMag  # b is already centered
        # unit vector of b
        unitB = np.stack((bx, by, bz))

        if quant == 'alf':
            uperb = obj.get_var('uperb')
            uperbVect = uperb * unitB
            # cross product (uses cstagger bc no variable gets uperbVect)
            curlX = (cstagger.do(cstagger.do(uperbVect[2], 'ddydn'), 'yup') -
                     cstagger.do(cstagger.do(uperbVect[1], 'ddzdn'), 'zup'))
            curlY = (-cstagger.do(cstagger.do(uperbVect[2], 'ddxdn'), 'xup')
                     +cstagger.do(cstagger.do(uperbVect[0], 'ddzdn'), 'zup'))
            curlZ = (cstagger.do(cstagger.do(uperbVect[1], 'ddxdn'), 'xup') -
                     cstagger.do(cstagger.do(uperbVect[0], 'ddydn'), 'yup'))
            curl = np.stack((curlX, curlY, curlZ))
            # dot product
            result = np.abs((unitB * curl).sum(0))
        elif quant == 'fast':
            uperb = obj.get_var('uperb')
            uperbVect = uperb * unitB

            result = np.abs(cstagger.do(cstagger.do(
                uperbVect[0], 'ddxdn'), 'xup') + cstagger.do(cstagger.do(
                    uperbVect[1], 'ddydn'), 'yup') + cstagger.do(
                        cstagger.do(uperbVect[2], 'ddzdn'), 'zup'))
        else:
            dot1 = obj.get_var('uparb')
            grad = np.stack((cstagger.do(cstagger.do(dot1, 'ddxdn'),
                                         'xup'), cstagger.do(cstagger.do(
                                             dot1, 'ddydn'), 'yup'),
                             cstagger.do(cstagger.do(dot1, 'ddzdn'),
                                         'zup')))
            result = np.abs((unitB * grad).sum(0))
        return result
    else:
        return None



def get_cyclo_res(obj, quant, CYCL_RES=None):

    if (CYCL_RES is None):
        CYCL_RES = ['n6nhe2', 'n6nhe3', 'nhe2nhe3']
        obj.description['CYCL_RES'] = ('Resonant cyclotron frequencies'
            '(only for do_helium) are (SI units): ' + ', '.join(CYCL_RES))
        obj.description['ALL'] += "\n"+ obj.description['CYCL_RES']

    if (quant == ''):
        return None

    if quant in CYCL_RES:
        if obj.hion and obj.heion:
            posn = ([pos for pos, char in enumerate(quant) if char == 'n'])
            q2 = quant[posn[-1]:]
            q1 = quant[:posn[-1]]
            if obj.hion:
                nel = obj.get_var('hionne')
            else:
                nel = obj.get_var('nel')
            var2 = obj.get_var(q2)
            var1 = obj.get_var(q1)
            z1= 1.0
            z2= float(quant[-1])
            if q1[:3] == 'n6':
                omega1 = obj.get_var('gfh2')
            else:
                omega1 = obj.get_var('gf'+q1[1:])
            omega2 = obj.get_var('gf'+q2[1:])
            return (z1 * var1 * omega2 + z2 * var2 * omega1) / nel
        else:
            raise ValueError(('get_quantity: This variable is only '
                              'avaiable if do_hion and do_helium is true'))
    else:
        return None


def get_gyrof(obj, quant, GYROF_QUANT=None):

    if (GYROF_QUANT is None):
        GYROF_QUANT = ['gfe'] + ['gf' + clist for clist in elemlist]
        obj.description['GYROF'] = ('gyro freqency are (Hz): ' +
            ', '.join(GYROF_QUANT) + ' at the end it must have the ionization' +
            'state, e,g, gfh2 is for ionized hydrogen')
        obj.description['ALL'] += "\n"+ obj.description['GYROF']

    if (quant == ''):
        return None

    if ''.join([i for i in quant if not i.isdigit()]) in GYROF_QUANT:
        if quant == 'gfe':
            return obj.get_var('modb') * obj.uni.usi_b * \
                obj.uni.qsi_electron / (obj.uni.msi_e)
        else:
            ion = float(''.join([i for i in quant if i.isdigit()]))
            return obj.get_var('modb') * obj.uni.usi_b * \
                obj.uni.qsi_electron * \
                (ion - 1.0) / \
                (obj.uni.weightdic[quant[2:-1]] * obj.uni.amusi)
    else:
        return None


def get_kappa(obj, quant, KAPPA_QUANT=None):

    if (KAPPA_QUANT is None):
        KAPPA_QUANT = ['kappanorm_','kappae'] + ['kappa' + clist for clist in elemlist]
        obj.description['KAPPA'] = ('kappa, i.e., magnetization are (adimensional): ' +
            ', '.join(KAPPA_QUANT) + ' at the end it must have the ionization' +
            'state, e,g, kappah2 is for protons')

    if (quant == ''):
        return None

    if ''.join([i for i in quant if not i.isdigit()]) in KAPPA_QUANT:
        if quant == 'kappae':
            return obj.get_var('gfe') / (obj.get_var('nu_en') + 1e-28)
        else:
            elem = quant.replace('kappa', '')
            return obj.get_var('gf'+elem) / (obj.get_var('nu'+elem+'_n') + 1e-28)

    elif quant[:-1] in KAPPA_QUANT or quant[:-2] in KAPPA_QUANT:
        elem = quant.split('_')
        return obj.get_var('kappah2')**2/(obj.get_var('kappah2')**2 +1) - \
            obj.get_var('kappa%s2'%elem[1])**2/(obj.get_var('kappa%s2'%elem[1])**2 +1)
    else:
        return None


def get_debye_ln(obj, quant, DEBYE_LN_QUANT=None):

    if (DEBYE_LN_QUANT is None):
        DEBYE_LN_QUANT = ['debye_ln']
        obj.description['DEBYE'] = ('Debye length in ... units:' +
            ', '.join(DEBYE_LN_QUANT))
        obj.description['ALL'] += "\n"+ obj.description['DEBYE']

    if (quant == ''):
        return None

    if quant in DEBYE_LN_QUANT:
        tg = obj.get_var('tg')
        part = np.copy(obj.get_var('ne'))
        # We are assuming a single charge state:
        for iele in elemlist:
            part += obj.get_var('n' + iele + '-2')
        if obj.heion:
            part += 4.0 * obj.get_var('nhe3')
        # check units of n
        return np.sqrt(obj.uni.permsi / obj.uni.qsi_electron**2 /
                       (obj.uni.ksi_b * tg.astype('Float64') *
                        part.astype('Float64') + 1.0e-20))
    else:
        return None


def get_ionpopulations(obj, quant, IONP_QUANT=None):

    if (IONP_QUANT is None):
        IONP_QUANT = ['n' + clist + '-' for clist in elemlist]
        IONP_QUANT += ['r' + clist + '-' for clist in elemlist]
        IONP_QUANT += ['rneu','rion','nion','nneu']
        IONP_QUANT += ['rneu_mag','rion_mag','nion_mag','nneu_mag']
        obj.description['IONP'] = ('densities for specific ionized species as'
            'follow (in SI): ' + ', '.join(IONP_QUANT))
        obj.description['ALL'] += "\n"+ obj.description['IONP']

    if (quant == ''):
        return None

    if ((quant in IONP_QUANT) and  (quant[-3:] in ['ion','neu'])):
            if quant[-3:] == 'ion':
                lvl = '2'
            else:
                lvl = '1'
            result = np.zeros(np.shape(obj.r))
            for ielem in elemlist:
                result += obj.get_var(quant[0]+ielem+'-'+lvl)
            return result

    elif ((quant in IONP_QUANT) and (quant[-7:] in ['ion_mag','neu_mag'])):
        if quant[-3:] == 'ion':
            lvl = '2'
        else:
            lvl = '1'
        result = np.zeros(np.shape(obj.r))
        if quant[-7:] == 'ion_mag':
            for ielem in elemlist[2:]:
                result += obj.get_var(quant[0]+ielem+'-'+lvl)*(1- obj.get_var('kappanorm_%s'%ielem))
        else:
            for ielem in elemlist[2:]:
                result += obj.get_var(quant[0]+ielem+'-'+lvl)*obj.get_var('kappanorm_%s'%ielem)
        return result

    elif ''.join([i for i in quant if not i.isdigit()]) in IONP_QUANT:
        elem = quant.replace('-','')
        spic = ''.join([i for i in elem if not i.isdigit()])
        lvl = ''.join([i for i in elem if i.isdigit()])

        if obj.hion and spic[1:] == 'h':
            if quant[0] == 'n':
                mass = 1.0
            else:
                mass = obj.uni.m_h
            if lvl == '1':
                return mass * (obj.get_var('n1') +
                               obj.get_var('n2') + obj.get_var('n3') +
                               obj.get_var('n4') + obj.get_var('n5'))
            else:
                return mass * obj.get_var('n6')

        elif obj.heion and spic[1:] == 'he':
            if quant[0] == 'n':
                mass = 1.0
            else:
                mass = obj.uni.m_he
            if obj.verbose:
                print('get_var: reading nhe%s' % lvl, whsp*5, end="\r",
                    flush=True)
            return mass * obj.get_var('nhe%s' % lvl)

        else:
            tg = obj.get_var('tg')
            r = obj.get_var('r')
            nel = obj.get_var('ne') / 1e6  # 1e6 conversion from SI to cgs

            if quant[0] == 'n':
                dens = False
            else:
                dens = True
            return ionpopulation(r, nel, tg, elem=spic[1:], lvl=lvl,
                                 dens=dens)
    else:
        return None


def get_ambparam(obj, quant, AMB_QUANT=None):

    if (AMB_QUANT is None):
        AMB_QUANT = ['uambx','uamby','uambz','ambx','amby','ambz',
                    'eta_amb1','eta_amb2','eta_amb3','eta_amb4','eta_amb5',
                    'chi','psi','chi_red','psi_red']
        obj.description['AMB'] = ('ambipolar velocity or term as'
            'follow (in Bifrost units): ' + ', '.join(AMB_QUANT))
        obj.description['ALL'] += "\n"+ obj.description['AMB']

    if (quant == ''):
        return None

    if (quant in AMB_QUANT):
        axis = quant[-1]
        if quant[0] == 'u':
            result = obj.get_var('jxb' + quant[-1]) / dd.get_var('modb') * dd.get_var('eta_amb')

        elif quant[:-1] != 'eta_amb' and quant[:3] != 'chi' and quant[:3] != 'psi' :
            if axis == 'x':
                varsn = ['y', 'z']
            elif axis == 'y':
                varsn = ['z', 'y']
            elif axis == 'z':
                varsn = ['x', 'y']
            result = (obj.get_var('jxb' + varsn[0]) *
                obj.get_var('b' + varsn[1] + 'c') -
                obj.get_var('jxb' + varsn[1]) *
                obj.get_var('b' + varsn[0] + 'c')) / dd.get_var('b2') * dd.get_var('eta_amb')

        elif quant == 'eta_amb1': # version from other
            result = (obj.get_var('rneu') / obj.get_var('r') * obj.uni.u_b)**2
            result /= (4.0 * obj.uni.pi * obj.get_var('nu_ni') + 1e-20)
            result *= obj.get_var('b2') / 1e7

        elif quant == 'eta_amb2': # Our version
            result = (obj.get_var('rneu') / obj.r * obj.uni.u_b)**2 / (
                4.0 * obj.uni.pi * obj.get_var('nu_nis') + 1e-20)
            result *= obj.get_var('b2') / 1e7

        elif quant == 'eta_amb3': # This should be the same and eta_amb2 except that eta_amb2 has many more species involved.
            result = (obj.get_var('rneu') / obj.r * obj.uni.u_b)**2 / (
                4.0 * obj.uni.pi * obj.get_var('nu_ins') + 1e-20)
            result *= obj.get_var('b2') / 1e7

        elif quant == 'eta_amb4': # This version takes into account the magnetization
            result = ((obj.get_var('rneu') + obj.get_var('rneu_mag')) / obj.r * obj.uni.u_b)**2 / (
                4.0 * obj.uni.pi * obj.get_var('nu_nis_mag') + 1e-20)
            result *= obj.get_var('b2') / 1e7

        elif quant == 'eta_amb5': # Yakov, Eq ()
            psi = obj.get_var('psi_red')
            chi = obj.get_var('chi_red')

            result = obj.get_var('modb') *(psi / (psi**2 +chi**2) - 1.0 / (
                    obj.get_var('hionne') * obj.get_var('kappae') + 1e-20))


        elif quant == 'chi':
            result = obj.r*0.0

            for iele in elemlist:
                result += (obj.get_var('kappae') +
                    obj.get_var('kappa'+iele+'2')) * (
                    obj.get_var('kappae') - obj.get_var('kappa'+iele+'2')) / (
                    1.0 + obj.get_var('kappa'+iele+'2')**2) / (
                    1.0 + obj.get_var('kappae')**2) * obj.get_var('n'+iele+'-2')

        elif quant == 'psi': # Yakov, Eq ()
            result = obj.r*0.0
            for iele in elemlist:
                result += (obj.get_var('kappae') +
                    obj.get_var('kappa'+iele+'2')) * (
                    1.0 + obj.get_var('kappae') * obj.get_var('kappa'+iele+'2')) / (
                    1.0 + obj.get_var('kappa'+iele+'2')**2) / (
                    1.0 + obj.get_var('kappae')**2) * obj.get_var('n'+iele+'-2')
        elif quant == 'chi_red': # alpha
            result = obj.r*0.0

            for iele in elemlist:
                result += 1.0 / (
                    1.0 + obj.get_var('kappa'+iele+'2')**2) * obj.get_var('n'+iele+'-2')

        elif quant == 'psi_red': # beta
            result = obj.r*0.0
            for iele in elemlist:
                result += obj.get_var('kappa'+iele+'2') / (
                    1.0 + obj.get_var('kappa'+iele+'2')**2) * obj.get_var('n'+iele+'-2')

        return  result
    else:
        return None

def get_hallparam(obj, quant, HALL_QUANT=None):

    if (HALL_QUANT is None):
        HALL_QUANT = ['uhallx','uhally','uhallz','hallx','hally','hallz']
        obj.description['HALL'] = ('Hall velocity or term as'
            'follow (in Bifrost units): ' + ', '.join(HALL_QUANT))
        obj.description['ALL'] += "\n"+ obj.description['HALL']

    if (quant == ''):
        return None

    if (quant in HALL_QUANT):
        if quant[0] == 'u':
            result = obj.get_var('j' + quant[-1])
        else:
            result = obj.get_var('jxb' + quant[-1]) / dd.get_var('modb')

        return dd.get_var('eta_hall') * result
    else:
        return None