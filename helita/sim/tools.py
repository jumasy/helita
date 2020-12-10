from astropy.io import fits
import numpy as np

def writefits(obj, varname, snap=None, instrument = 'MURaM', 
              name='ar098192', origin='HGCR    '): 

  if varname[:2] == 'lg': 
    varnamefits='lg('+varname[2:]+')'
  else: 
    varnamefits = varname

  hdu = fits.PrimaryHDU(obj.datafits)
  hdu.header['NAXIS']  = np.ndim(obj.datafits)
  hdu.header['NAXIS1'] = np.shape(obj.datafits)[0]
  hdu.header['NAXIS2'] = np.shape(obj.datafits)[1]
  hdu.header['NAXIS3'] = np.shape(obj.datafits)[2]
  hdu.header['EXTENT'] = 'T'
  hdu.header['INSTRUME'] = instrument
  hdu.header['OBJECT'] = name
  hdu.header['BTYPE']  = varnamefits
  hdu.header['BUNIT']  = obj.fitsunits # SI units
  hdu.header['CDELT1'] = obj.dxfits.min()
  hdu.header['CDELT2'] = obj.dyfits.min()
  hdu.header['CDELT3'] = obj.dzfits.min()
  hdu.header['CRPIX1'] = 1
  hdu.header['CRPIX2'] = 1
  hdu.header['CRPIX3'] = 1
  hdu.header['CRVAL1'] = obj.xfits.min()
  hdu.header['CRVAL2'] = obj.yfits.min()
  hdu.header['CRVAL3'] = obj.zfits.min()
  hdu.header['CTYPE1'] = 'x       '
  hdu.header['CTYPE2'] = 'y       '
  hdu.header['CTYPE3'] = 'z       '
  hdu.header['CUNIT1'] = 'Mm      '
  hdu.header['CUNIT2'] = 'Mm      '
  hdu.header['CUNIT3'] = 'Mm      '
  hdu.header['RUNID']  = 'hgcr    '
  hdu.header['ELAPSED']= obj.time
  hdu.header['DATA_LEV']  = 2
  hdu.header['ORIGIN'] = origin 
  hdu.header['MX']     = np.shape(obj.datafits)[0]
  hdu.header['MY']     = np.shape(obj.datafits)[1]
  hdu.header['MZ']     = np.shape(obj.datafits)[2]
  hdu.header['NDIM']   = np.ndim(obj.datafits)
  hdu.header['DX']     = obj.dxfits.min()
  hdu.header['DY']     = obj.dyfits.min()
  hdu.header['DZ']     = obj.dzfits.min()
  hdu.header['T']      = obj.time

  hdu1 = fits.ImageHDU(obj.zfits)
  hdu1.header['XTENSION']= 'IMAGE   '           # IMAGE extension                                
  hdu1.header['BITPIX']  =                  -32 # Number of bits per data pixel                  
  hdu1.header['NAXIS']   =                    1 # Number of data axes                            
  hdu1.header['NAXIS1']  =      np.size(obj.zfits)   
  hdu1.header['PCOUNT']  =                    0 # No Group Parameters                            
  hdu1.header['GCOUNT']  =                    1 # One Data Group                                 
  hdu1.header['EXTNAME'] = ' z-coordinate'                                                      
  hdu1.header['BTYPE']   = 'z       '           # Data variable                                  
  hdu1.header['BUNIT']   = 'Mm      '           # Unit for z-coordinate    
  hdul = fits.HDUList([hdu,hdu1])
  hdul.writeto(instrument+'_'+name+'_'+varname+'_'+inttostring(obj.snap)+'.fits')


def inttostring(ii,ts_size=7):

  str_num = str(ii)

  for bb in range(len(str_num),ts_size,1):
    str_num = '0'+str_num
  
  return str_num


def units_title(obj): 
  '''
  Units and constants in SI
  '''
  obj.unisi_title={}
  obj.unisi_title['tg']     = ' K '
  obj.unisi_title['l']      = ' m '
  obj.unisi_title['pg']     = ' N m^(-2) '
  obj.unisi_title['rho']    = ' g m^{-3} '
  obj.unisi_title['u']      = ' m s^{-1} '
  obj.unisi_title['b']      = ' T ' # Tesla
  obj.unisi_title['e']      = ' J m^(-3) '
  obj.unisi_title['t']      = ' s ' # seconds

def convertcsgsi(obj):
  
  import scipy.constants as const
  
  '''
  Conversion from cgs units to SI
  '''

  obj.unisi={}
  obj.unisi['proton'] = 1.67262158e-27 # kg
  #obj.uni['kboltz'] = 1.380658e-16 
  obj.unisi['c']      = 299792.458 * 1e3 #m/s
  obj.unisi['tg']     = obj.uni['tg'] # K
  obj.unisi['t']      = obj.uni['t'] # seconds
  obj.unisi['l']      = obj.uni['l'] * const.centi # m
  obj.unisi['rho']    = obj.uni['rho'] * const.gram / const.centi**3 # kg m^-3 
  obj.unisi['u']      = obj.uni['u'] * const.centi # m/s
  obj.unisi['b']      = obj.uni['b'] * 1e-4 # T
  obj.unisi['j']      = 1.0 # current density  
  obj.unisi['pg']     = obj.unisi['rho'] * (obj.unisi['l'] / obj.unisi['t'])**2
  obj.unisi['ee']     = obj.unisi['u']**2
  obj.unisi['e']      = obj.unisi['rho'] * obj.unisi['ee'] 


def globalvars(obj):
    
  import scipy.constants as const
  
  '''
  Conversion from cgs units to SI
  '''

  obj.mu = 0.8
  obj.k_b = aconst.k_B.to_value('erg/K')  # 1.380658E-16 Boltzman's cst. [erg/K]
  obj.m_h = const.m_n / const.gram        # 1.674927471e-24
  obj.m_he = 6.65e-24
  obj.m_p = obj.mu * obj.m_h            # Mass per particle
  obj.m_e = aconst.m_e.to_value('g')

  obj.ksi_b = aconst.k_B.to_value('J/K')               # Boltzman's cst. [J/K]
  obj.msi_h = const.m_n                                # 1.674927471e-27
  obj.msi_he = 6.65e-27
  obj.msi_p = obj.mu * obj.msi_h                     # Mass per particle
  obj.msi_e = const.m_e  # 9.1093897e-31

  # Solar gravity
  obj.gsun = (aconst.GM_sun / aconst.R_sun**2).cgs.value  # solar surface gravity

  # --- physical constants and other useful quantities
  obj.clight = aconst.c.to_value('cm/s')   # Speed of light [cm/s]
  obj.hplanck = aconst.h.to_value('erg s') # Planck's constant [erg s]
  obj.hplancksi = aconst.h.to_value('J s') # Planck's constant [erg s]
  obj.kboltzmann = aconst.k_B.to_value('erg/K')  # Boltzman's cst. [erg/K]
  obj.amu = aconst.u.to_value('g')        # Atomic mass unit [g]
  obj.amusi = aconst.u.to_value('kg')     # Atomic mass unit [kg]
  obj.m_electron = aconst.m_e.to_value('g')  # Electron mass [g]
  obj.q_electron = aconst.e.esu.value     # Electron charge [esu]
  obj.qsi_electron = aconst.e.value       # Electron charge [C]
  obj.rbohr = aconst.a0.to_value('cm')    #  bohr radius [cm]
  obj.e_rydberg = aconst.Ryd.to_value('erg', equivalencies=units.spectral())
  obj.eh2diss = 4.478007          # H2 dissociation energy [eV]
  obj.pie2_mec = (np.pi * aconst.e.esu **2 / (aconst.m_e * aconst.c)).cgs.value
  # 5.670400e-5 Stefan-Boltzmann constant [erg/(cm^2 s K^4)]
  obj.stefboltz = aconst.sigma_sb.cgs.value
  obj.mion = obj.m_h            # Ion mass [g]
  obj.r_ei = 1.44E-7        # e^2 / kT = 1.44x10^-7 T^-1 cm

  # --- Unit conversions
  obj.ev_to_erg = units.eV.to('erg')
  obj.ev_to_j = units.eV.to('J')
  obj.nm_to_m = const.nano   # 1.0e-09
  obj.cm_to_m = const.centi  # 1.0e-02
  obj.km_to_m = const.kilo   # 1.0e+03
  obj.erg_to_joule = const.erg  # 1.0e-07
  obj.g_to_kg = const.gram   # 1.0e-03
  obj.micron_to_nm = units.um.to('nm')
  obj.megabarn_to_m2 = units.Mbarn.to('m2')
  obj.atm_to_pa = const.atm  # 1.0135e+05 atm to pascal (n/m^2)
  obj.dyne_cm2_to_pascal = (units.dyne / units.cm**2).to('Pa')
  obj.k_to_ev = units.K.to('eV', equivalencies=units.temperature_energy())
  obj.ev_to_k = 1. / obj.k_to_ev
  obj.ergd2wd = 0.1
  obj.grph = 2.27e-24
  obj.permsi = aconst.eps0.value  # Permitivitty in vacuum (F/m)
  obj.cross_p = 1.59880e-14
  obj.cross_he = 9.10010e-17

  # Dissociation energy of H2 [eV] from Barklem & Collet (2016)
  obj.di = obj.eh2diss

  obj.atomdic = {'h': 1, 'he': 2, 'c': 3, 'n': 4, 'o': 5, 'ne': 6, 'na': 7,
             'mg': 8, 'al': 9, 'si': 10, 's': 11, 'k': 12, 'ca': 13,
             'cr': 14, 'fe': 15, 'ni': 16}
  obj.abnddic = {'h': 12.0, 'he': 11.0, 'c': 8.55, 'n': 7.93, 'o': 8.77,
             'ne': 8.51, 'na': 6.18, 'mg': 7.48, 'al': 6.4, 'si': 7.55,
             's': 5.21, 'k': 5.05, 'ca': 6.33, 'cr': 5.47, 'fe': 7.5,
             'ni': 5.08}
  obj.weightdic = {'h': 1.008, 'he': 4.003, 'c': 12.01, 'n': 14.01,
               'o': 16.00, 'ne': 20.18, 'na': 23.00, 'mg': 24.32,
               'al': 26.97, 'si': 28.06, 's': 32.06, 'k': 39.10,
               'ca': 40.08, 'cr': 52.01, 'fe': 55.85, 'ni': 58.69}
  obj.xidic = {'h': 13.595, 'he': 24.580, 'c': 11.256, 'n': 14.529,
           'o': 13.614, 'ne': 21.559, 'na': 5.138, 'mg': 7.644,
           'al': 5.984, 'si': 8.149, 's': 10.357, 'k': 4.339,
           'ca': 6.111, 'cr': 6.763, 'fe': 7.896, 'ni': 7.633}
  obj.u0dic = {'h': 2., 'he': 1., 'c': 9.3, 'n': 4., 'o': 8.7,
           'ne': 1., 'na': 2., 'mg': 1., 'al': 5.9, 'si': 9.5, 's': 8.1,
           'k': 2.1, 'ca': 1.2, 'cr': 10.5, 'fe': 26.9, 'ni': 29.5}
  obj.u1dic = {'h': 1., 'he': 2., 'c': 6., 'n': 9.,  'o': 4.,  'ne': 5.,
           'na': 1., 'mg': 2., 'al': 1., 'si': 5.7, 's': 4.1, 'k': 1.,
           'ca': 2.2, 'cr': 7.2, 'fe': 42.7, 'ni': 10.5}



def polar2cartesian(r, t, grid, x, y, order=3):
    '''
    Converts polar grid to cartesian grid
    '''


    X, Y = np.meshgrid(x, y)

    new_r = np.sqrt(X * X + Y * Y)
    new_t = np.arctan2(X, Y)

    ir = interpolate.interp1d(r, np.arange(len(r)), bounds_error=False)
    it = interpolate.interp1d(t, np.arange(len(t)))

    new_ir = ir(new_r.ravel())
    new_it = it(new_t.ravel())

    new_ir[new_r.ravel() > r.max()] = len(r) - 1
    new_ir[new_r.ravel() < r.min()] = 0

    return map_coordinates(grid, np.array([new_ir, new_it]),
                           order=order).reshape(new_r.shape)


def cartesian2polar(x, y, grid, r, t, order=3):
    '''
    Converts cartesian grid to polar grid
    '''

    R, T = np.meshgrid(r, t)

    new_x = R * np.cos(T)
    new_y = R * np.sin(T)

    ix = interpolate.interp1d(x, np.arange(len(x)), bounds_error=False)
    iy = interpolate.interp1d(y, np.arange(len(y)), bounds_error=False)

    new_ix = ix(new_x.ravel())
    new_iy = iy(new_y.ravel())

    new_ix[new_x.ravel() > x.max()] = len(x) - 1
    new_ix[new_x.ravel() < x.min()] = 0

    new_iy[new_y.ravel() > y.max()] = len(y) - 1
    new_iy[new_y.ravel() < y.min()] = 0

    return map_coordinates(grid, np.array([new_ix, new_iy]),
                           order=order).reshape(new_x.shape)

