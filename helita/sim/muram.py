# import builtin modules
import os
import ast
import time
import weakref
import warnings
import functools
import collections
from glob import glob

# import external public modules
import numpy as np
from scipy import interpolate
from scipy.ndimage import map_coordinates

from .bifrost import Rhoeetab
from .load_arithmetic_quantities import *
from .load_quantities import *
from .tools import *

from . import document_vars, file_memory, load_fromfile_quantities, stagger, tools, units


class MuramAtmos:
    """
    Class to read MURaM atmosphere

    Parameters
    ----------
    fdir : str, optional
        Directory with snapshots.
    template : str, optional
        Template for snapshot number.
    verbose : bool, optional
        If True, will print more information.
    dtype : str or numpy.dtype, optional
        Datatype of read data.
    big_endian : bool, optional
        Endianness of output file. Default is False (little endian).
    prim : bool, optional
        Set to True if moments are written instead of velocities.
    """

    def __init__(self, fdir='.', template=".020000", verbose=True, dtype='f4',
                 sel_units='cgs', big_endian=False, prim=False, iz0=None, inttostring=(lambda x: '{0:07d}'.format(x))):

        self.prim = prim
        self.fdir = fdir
        self.verbose = verbose
        self.sel_units = sel_units
        self.iz0 = iz0
        # endianness and data type
        if big_endian:
            self.dtype = '>' + dtype
        else:
            self.dtype = '<' + dtype
        self.uni = Muram_units(filename=None, parent=self)
        self.read_header("%s/Header%s" % (fdir, template))
        #self.read_atmos(fdir, template)
        # Snapshot number
        self.snap = int(template[1:])
        self.filename = ''
        self.inttostring = inttostring
        self.siter = template
        self.file_root = template

        self.transunits = False
        self.lowbus = False

        self.do_stagger = False
        self.hion = False  # This will not allow to use HION from Bifrost in load
        self.heion = False
        tabfile = os.path.join(self.fdir, 'tabparam.in')

        self.cross_sect = cross_sect_for_obj(self)

        if os.access(tabfile, os.R_OK):
            self.rhoee = Rhoeetab(tabfile=tabfile, fdir=fdir, radtab=False)

        self.genvar(order=self.order)

        document_vars.create_vardict(self)
        document_vars.set_vardocs(self)

    size = property(lambda self: (self.xLength * self.yLength * self.zLength))
    ndim = property(lambda self: 3)
    shape = property(lambda self: (self.xLength, self.yLength, self.zLength))


    def read_header(self, headerfile):
        tmp = np.loadtxt(headerfile)
        #self.dims_orig = tmp[:3].astype("i")
        dims = tmp[:3].astype("i")
        deltas = tmp[3:6]
        # if len(tmp) == 10: # Old version of MURaM, deltas stored in km
        #    self.uni.uni['l'] = 1e5 # JMS What is this for?

        self.time = tmp[6]

        layout = np.loadtxt('layout.order')
        self.order = layout[0:3].astype(int)
        # if len(self.order) == 0:
        #    self.order = np.array([0,2,1]).astype(int)
        #self.order = tmp[-3:].astype(int)
        # dims = [1,2,0] 0=z,
        #dims = np.array((self.dims_orig[self.order[2]],self.dims_orig[self.order[0]],self.dims_orig[self.order[1]]))
        #deltas = np.array((deltas[self.order[2]],deltas[self.order[0]],deltas[self.order[1]])).astype('float32')
        deltas = deltas[self.order]
        dims = dims[self.order]

        if self.sel_units == 'cgs':
            deltas *= self.uni.uni['l']

        self.x = np.arange(dims[0])*deltas[0]
        self.y = np.arange(dims[1])*deltas[1]
        self.z = np.arange(dims[2])*deltas[2]
        if self.iz0 != None:
            self.z = self.z - self.z[self.iz0]
        self.dx, self.dy, self.dz = deltas[0], deltas[1], deltas[2]
        self.nx, self.ny, self.nz = dims[0], dims[1], dims[2]

        if self.nx > 1:
            self.dx1d = np.gradient(self.x)
        else:
            self.dx1d = np.zeros(self.nx)

        if self.ny > 1:
            self.dy1d = np.gradient(self.y)
        else:
            self.dy1d = np.zeros(self.ny)

        if self.nz > 1:
            self.dz1d = np.gradient(self.z)
        else:
            self.dz1d = np.zeros(self.nz)

    def read_atmos(self, fdir, template):
        ashape = (self.nx, self.nz, self.ny)
        file_T = "%s/eosT%s" % (fdir, template)
        # When 0-th dimension is vertical, 1st is x, 2nd is y
        # when 1st dimension is vertical, 0th is x.
        # remember to swap names

        bfact = np.sqrt(4 * np.pi)
        if os.path.isfile(file_T):
            self.tg = np.memmap(file_T, mode="r", shape=ashape,
                                dtype=self.dtype,
                                order="F")
        file_press = "%s/eosP%s" % (fdir, template)
        if os.path.isfile(file_press):
            self.pressure = np.memmap(file_press, mode="r", shape=ashape,
                                      dtype=self.dtype,
                                      order="F")
        file_ne = "%s/eosne%s" % (fdir, template)
        if os.path.isfile(file_ne):
            self.ne = np.memmap(file_ne, mode="r", shape=ashape,
                                      dtype=self.dtype,
                                      order="F")
        file_rho = "%s/result_prim_0%s" % (fdir, template)
        if os.path.isfile(file_rho):
            self.rho = np.memmap(file_rho, mode="r", shape=ashape,
                                 dtype=self.dtype,
                                 order="F")
        file_vx = "%s/result_prim_1%s" % (fdir, template)
        if os.path.isfile(file_vx):
            self.vx = np.memmap(file_vx, mode="r", shape=ashape,
                                dtype=self.dtype,
                                order="F")
        file_vz = "%s/result_prim_2%s" % (fdir, template)
        if os.path.isfile(file_vz):
            self.vz = np.memmap(file_vz, mode="r", shape=ashape,
                                dtype=self.dtype,
                                order="F")
        file_vy = "%s/result_prim_3%s" % (fdir, template)
        if os.path.isfile(file_vy):
            self.vy = np.memmap(file_vy, mode="r", shape=ashape,
                                dtype=self.dtype,
                                order="F")
        file_ei = "%s/result_prim_4%s" % (fdir, template)
        if os.path.isfile(file_ei):
            self.ei = np.memmap(file_ei, mode="r", shape=ashape,
                                dtype=self.dtype,
                                order="F")
        file_Bx = "%s/result_prim_5%s" % (fdir, template)
        if os.path.isfile(file_Bx):
            self.bx = np.memmap(file_Bx, mode="r", shape=ashape,
                                dtype=self.dtype,
                                order="F")
            self.bx = self.bx * bfact
        file_Bz = "%s/result_prim_6%s" % (fdir, template)
        if os.path.isfile(file_Bz):
            self.bz = np.memmap(file_Bz, mode="r", shape=ashape,
                                dtype=self.dtype,
                                order="F")
            self.bz = self.bz * bfact
        file_By = "%s/result_prim_7%s" % (fdir, template)
        if os.path.isfile(file_By):
            self.by = np.memmap(file_By, mode="r", shape=ashape,
                                dtype=self.dtype,
                                order="F")
            self.by = self.by * bfact
        file_tau = "%s/tau%s" % (fdir, template)
        if os.path.isfile(file_tau):
            self.tau = np.memmap(file_tau, mode="r", shape=ashape,
                                 dtype=self.dtype,
                                 order="F")
        file_Qtot = "%s/Qtot%s" % (fdir, template)
        if os.path.isfile(file_Qtot):
            self.qtot = np.memmap(file_Qtot, mode="r", shape=ashape,
                                  dtype=self.dtype,
                                  order="F")

        # from moments to velocities
        # if self.prim:
        #    if hasattr(self,'rho'):
        #        if hasattr(self,'vx'):
        #            self.vx /= self.rho
        #        if hasattr(self,'vy'):
        #            self.vy /= self.rho
        #        if hasattr(self,'vz'):
        #            self.vz /= self.rho

    def read_Iout(self):

        tmp = np.fromfile(self.fdir+'I_out.'+self.siter)

        size = tmp[1:3].astype(int)
        time = tmp[3]

        return tmp[4:].reshape([size[1], size[0]]).swapaxes(0, 1), size, time

    def read_slice(self, var, depth):

        tmp = np.fromfile(self.fdir+var+'_slice_'+depth+'.'+self.siter)

        nslices = tmp[0].astype(int)
        size = tmp[1:3].astype(int)
        time = tmp[3]

        return tmp[4:].reshape([nslices, size[1], size[0]]).swapaxes(1, 2), nslices, size, time

    def read_dem(self, path, max_bins=None):

        tmp = np.fromfile(path+'corona_emission_adj_dem_'+self.fdir+'.'+self.siter)

        bins = tmp[0].astype(int)
        size = tmp[1:3].astype(int)
        time = tmp[3]
        lgTmin = tmp[4]
        dellgT = tmp[5]

        dem = tmp[6:].reshape([bins, size[1], size[0]]).transpose(2, 1, 0)

        taxis = lgTmin+dellgT*np.arange(0, bins+1)

        X_H = 0.7
        dem = dem*X_H*0.5*(1+X_H)*3.6e19

        if max_bins != None:
            if bins > max_bins:
                dem = dem[:, :, 0:max_bins]
            else:
                tmp = dem
                dem = np.zeros([size[0], size[1], max_bins])
                dem[:, :, 0:bins] = tmp

            taxis = lgTmin+dellgT*np.arange(0, max_bins+1)

        return dem, taxis, time

    def _load_quantity(self, var, cgsunits=1.0, **kwargs):
        '''helper function for get_var; actually calls load_quantities for var.'''
        __tracebackhide__ = True  # hide this func from error traceback stack
        # look for var in self.variables
        if (var == 'ne'):
            print('WWW: Reading ne from Bifrost EOS', end="\r", flush=True)

        # Try to load simple quantities.
        # val = load_fromfile_quantities.load_fromfile_quantities(self, var,
        #                                        save_if_composite=True, **kwargs)
        # if val is not None:
        #    val = val * cgsunits  # (vars from load_fromfile need to get hit by cgsunits.)
        # Try to load "regular" quantities
        # if val is None:
        val = load_quantities(self, var, PLASMA_QUANT='', CYCL_RES='',
                              COLFRE_QUANT=None, COLFRI_QUANT=None, IONP_QUANT=None,
                              EOSTAB_QUANT=['ne', 'tau'], TAU_QUANT='', DEBYE_LN_QUANT='',
                              CROSTAB_QUANT=None, COULOMB_COL_QUANT=None, AMB_QUANT=None,
                              HALL_QUANT=None, BATTERY_QUANT=None, SPITZER_QUANT='',
                              KAPPA_QUANT='', GYROF_QUANT=None, WAVE_QUANT='',
                              FLUX_QUANT='', CURRENT_QUANT=None, COLCOU_QUANT=None,
                              COLCOUMS_QUANT=None, COLFREMX_QUANT=None, **kwargs)

        # Try to load "arithmetic" quantities.
        if val is None:
            val = load_arithmetic_quantities(self, var, **kwargs)

        return val

    def get_var(self, var, snap=None, iix=None, iiy=None, iiz=None, layout=None, **kwargs):
        '''
        Reads the variables from a snapshot (snap).

        Parameters
        ----------
        var - string
            Name of the variable to read. Must be Bifrost internal names.
        snap - integer, optional
            Snapshot number to read. By default reads the loaded snapshot;
            if a different number is requested, will load that snapshot.

        Axes:
        -----
        For the hgcr model:
            y-axis is the vertical x and z-axes are horizontal
        Newer runs could have x-axis the vertical.

        Variable list:
        --------------
            result_prim_0 -- Density (g/cm^3)
            result_prim_1 -- component x of the velocity (cm/s)
            result_prim_2 -- component y of the velocity (cm/s), vertical in the hgcr
            result_prim_3 -- component z of the velocity (cm/s)
            result_prim_4 -- internal energy (erg)
            result_prim_5 -- component x of the magnetic field (G/sqrt(4*pi))
            result_prim_6 -- component y of the magnetic field (G/sqrt(4*pi))
            result_prim_7 -- component z of the magnetic field (G/sqrt(4*pi))
            eosP          -- Pressure (cgs)
            eosT          -- Temperature (K)
        '''

        if (not snap == None):
            self.snap = snap
            self.siter = '.'+self.inttostring(snap)
            self.read_header("%s/Header%s" % (self.fdir, self.siter))

        if var in self.varn.keys():
            varname = self.varn[var]
        else:
            varname = var

        if ((var in self.varn.keys()) and os.path.isfile(self.fdir+'/'+varname + self.siter)):
            ashape = np.array([self.nx, self.ny, self.nz])

            transpose_order = self.order

            if self.sel_units == 'cgs':
                varu = var.replace('x', '')
                varu = varu.replace('y', '')
                varu = varu.replace('z', '')
                if (var in self.varn.keys()) and (varu in self.uni.uni.keys()):
                    cgsunits = self.uni.uni[varu]
                else:
                    cgsunits = 1.0
            else:
                cgsunits = 1.0
            #orderfiles = [self.order[2],self.order[0],self.order[1]]

            # self.order = [2,0,1]
            data = np.memmap(self.fdir+'/'+varname + self.siter, mode="r",
                             shape=tuple(ashape[self.order[self.order]]),
                             dtype=self.dtype, order="F")
            data = data.transpose(transpose_order)

            if iix != None:
                data = data[iix, :, :]
            if iiy != None:
                data = data[:, iiy, :]
            if iiz != None:
                data = data[:, :, iiz]

            self.data = data * cgsunits

        else:
            # Loading quantities
            cgsunits = 1.0
            # get value of variable.
            self.data = self._load_quantity(var, cgsunits, **kwargs)

            # do post-processing
            # self.data = self._get_var_postprocess(self.data, var=var, original_slice=original_slice)

        return self.data

    ## GET VARIABLE ##
    def __call__(self, var, *args, **kwargs):
        '''equivalent to self.get_var(var, *args, **kwargs)'''
        __tracebackhide__ = True  # hide this func from error traceback stack
        return self.get_var(var, *args, **kwargs)

    def zero(self, **kw__np_zeros):
        '''return np.zeros() with shape equal to shape of result of get_var()'''
        return np.zeros(self.shape, **kw__np_zeros)

    def _get_var_postprocess(self, val, var='', original_slice=[slice(None) for x in ('x', 'y', 'z')]):
        '''does post-processing for get_var.
        This includes:
            - handle "creating documentation" or "var==''" case
            - handle "don't know how to get this var" case
            - reshape result as appropriate (based on iix,iiy,iiz)
        returns val after the processing is complete.
        '''
        # handle documentation case
        if document_vars.creating_vardict(self):
            return None
        elif var == '':
            print('Variables from snap or aux files:')
            print(self.simple_vars)
            if hasattr(self, 'vardict'):
                self.vardocs()
            return None

        # handle "don't know how to get this var" case
        if val is None:
            errmsg = ('get_var: do not know (yet) how to calculate quantity {}. '
                      '(Got None while trying to calculate it.) '
                      'Note that simple_var available variables are: {}. '
                      '\nIn addition, get_quantity can read others computed variables; '
                      "see e.g. help(self.get_var) or get_var('')) for guidance.")
            raise ValueError(errmsg.format(repr(var), repr(self.simple_vars)))

        # set original_slice if cstagop is enabled and we are at the outermost layer.
        if self.cstagop and not self._getting_internal_var():
            self.set_domain_iiaxes(*original_slice, internal=False)

        # reshape if necessary... E.g. if var is a simple var, and iix tells to slice array.
        if np.shape(val) != (self.xLength, self.yLength, self.zLength):
            def isslice(x): return isinstance(x, slice)
            if isslice(self.iix) and isslice(self.iiy) and isslice(self.iiz):
                val = val[self.iix, self.iiy, self.iiz]  # we can index all together
            else:  # we need to index separately due to numpy multidimensional index array rules.
                val = val[self.iix, :, :]
                val = val[:, self.iiy, :]
                val = val[:, :, self.iiz]

        return val

    def read_var_3d(self, var, iter=None, layout=None):

        if (not iter == None):
            self.siter = '.'+self.inttostring(iter)
            self.read_header("%s/Header%s" % (self.fdir, self.siter))

        tmp = np.fromfile(self.fdir+'/'+var + self.siter)
        self.data = tmp.reshape([self.nx, self.ny, self.nz])

        if layout != None:
            self.data = tmp.transpose(layout)

        return self.data

    def read_vlos(self, path, max_bins=None):

        tmp = np.fromfile(path+'corona_emission_adj_vlos_'+self.fdir+'.'+self.siter)

        bins = tmp[0].astype(int)
        size = tmp[1:3].astype(int)
        time = tmp[3]
        lgTmin = tmp[4]
        dellgT = tmp[5]

        vlos = tmp[6:].reshape([bins, self.ny, self.nz]).transpose(2, 1, 0)

        taxis = lgTmin+dellgT*np.arange(0, bins+1)

        if max_bins != None:
            if bins > max_bins:
                vlos = vlos[:, :, 0:max_bins]
            else:
                tmp = vlos
                vlos = np.zeros([self.nz, self.ny, max_bins])
                vlos[:, :, 0:bins] = tmp

            taxis = lgTmin+dellgT*np.arange(0, max_bins+1)

        return vlos, taxis, time

    def read_vrms(self, path, max_bins=None):

        tmp = np.fromfile(path+'corona_emission_adj_vrms_'+self.fdir+'.'+self.template)

        bins = tmp[0].astype(int)
        size = tmp[1:3].astype(int)
        time = tmp[3]
        lgTmin = tmp[4]
        dellgT = tmp[5]

        vlos = tmp[6:].reshape([bins, self.ny, self.nz]).transpose(2, 1, 0)

        taxis = lgTmin+dellgT*np.arange(0, bins+1)

        if max_bins != None:
            if bins > max_bins:
                vlos = vlos[:, :, 0:max_bins]
            else:
                tmp = vlos
                vlos = np.zeros([self.nz, self.ny, max_bins])
                vlos[:, :, 0:bins] = tmp

            taxis = lgTmin+dellgT*np.arange(0, max_bins+1)

        return vlos, taxis, time

    def read_fil(self, path, max_bins=None):

        tmp = np.fromfile(path+'corona_emission_adj_fil_'+self.fdir+'.'+self.template)
        bins = tmp[0].astype(int)
        size = tmp[1:3].astype(int)
        time = tmp[3]
        lgTmin = tmp[4]
        dellgT = tmp[5]

        vlos = tmp[6:].reshape([bins, size[1], size[0]]).transpose(2, 1, 0)

        taxis = lgTmin+dellgT*np.arange(0, bins+1)

        if max_bins != None:
            if bins > max_bins:
                vlos = vlos[:, :, 0:max_bins]
            else:
                tmp = vlos
                vlos = np.zeros([size[0], size[1], max_bins])
                vlos[:, :, 0:bins] = tmp

            taxis = lgTmin+dellgT*np.arange(0, max_bins+1)

        return vlos, taxis, time

    def genvar(self, order=[0, 1, 2]):
        '''
        Dictionary of original variables which will allow to convert to cgs.
        '''
        self.varn = {}
        self.varn['rho'] = 'result_prim_0'
        self.varn['totr'] = 'result_prim_0'
        self.varn['tg'] = 'eosT'
        self.varn['pg'] = 'eosP'
        if os.path.isfile(self.fdir+'/eosne' + self.siter):
            print('Has ne files')
            self.varn['ne'] = 'eosne'

        unames = np.array(['result_prim_1', 'result_prim_2', 'result_prim_3'])
        unames = unames[order]
        self.varn['ux'] = unames[0]
        self.varn['uy'] = unames[1]
        self.varn['uz'] = unames[2]
        self.varn['e'] = 'result_prim_4'
        unames = np.array(['result_prim_5', 'result_prim_6', 'result_prim_7'])
        unames = unames[order]
        self.varn['bx'] = unames[0]
        self.varn['by'] = unames[1]
        self.varn['bz'] = unames[2]

    def write_rh15d(self, outfile, desc=None, append=True, writeB=False,
                    sx=slice(None), sy=slice(None), sz=slice(None),
                    wght_per_h=1.4271):
        ''' Writes RH 1.5D NetCDF snapshot '''
        import scipy.constants as ct

        from . import rh15d

        # unit conversion to SI
        ul = 1.e-2  # to metres
        ur = 1.e3   # from g/cm^3 to kg/m^3
        ut = 1.     # to seconds
        ul / ut
        ub = 1.e-4  # to Tesla
        ue = 1.      # to erg/g
        # slicing and unit conversion (default slice of None selects all)
        if sx != slice(None):
            sx = slice(sx[0], sx[1], sx[2])
        if sy != slice(None):
            sy = slice(sy[0], sy[1], sy[2])
        if sz != slice(None):
            sz = slice(sz[0], sz[1], sz[2])
        print('Slicing and unit conversion...')
        temp = self.tg[sx, sy, sz]
        rho = self.rho[sx, sy, sz]
        rho = rho * ur
        if writeB:
            Bx = self.bx[sx, sy, sz]
            By = self.by[sx, sy, sz]
            Bz = self.bz[sx, sy, sz]
            Bx = Bx * ub
            By = By * ub
            Bz = Bz * ub
        else:
            Bx, By, Bz = [None] * 3
        vx = self.vx[sx, sy, sz] * ul
        vy = self.vy[sx, sy, sz] * ul
        vz = self.vz[sx, sy, sz] * ul
        x = self.x[sx] * ul
        y = self.y[sy] * ul
        z = self.z[sz] * ul
        # convert from rho to H atoms
        nh = rho / (wght_per_h * ct.atomic_mass)  # from rho to nH
        # description
        if desc is None:
            desc = 'MURAM shapshot sequence %s, sx=%s sy=%s sz=%s.' % \
                   (self.fdir, repr(sx), repr(sy), repr(sz))
        # write to file
        print('Write to file...')
        rh15d.make_xarray_atmos(outfile, temp, vz, z, nH=nh, x=x, y=y, vx=vx,
                                vy=vy, rho=rho, append=append, Bx=Bx, By=By,
                                Bz=Bz, desc=desc, snap=self.snap)

    def trans2comm(self, varname, snap=None):
        '''
        Transform the domain into a "common" format. All arrays will be 3D. The 3rd axis
        is:

          - for 3D atmospheres:  the vertical axis
          - for loop type atmospheres: along the loop
          - for 1D atmosphere: the unique dimension is the 3rd axis.
          At least one extra dimension needs to be created artifically.

        All of them should obey the right hand rule

        In all of them, the vectors (velocity, magnetic field etc) away from the Sun.

        If applies, z=0 near the photosphere.

        Units: everything is in cgs.

        If an array is reverse, do ndarray.copy(), otherwise pytorch will complain.

        '''

        self.sel_units = 'cgs'

        self.trans2commaxes

        return self.get_var(varname, snap=snap)

    def trans2commaxes(self):

        if self.transunits == False:
            self.transunits = True

    def trans2noncommaxes(self):

        if self.transunits == True:
            self.transunits = False

    def trasn2fits(self, varname, snap=None, instrument='MURaM',
                   name='ar098192', origin='HGCR    ', z_tau51m=None, iz0=None):
        '''
        converts the original data into fits files following Bifrost publicly available
        format, i.e., SI, vertical axis, z and top corona is positive and last index.
        '''

        if varname[-1] == 'x':
            varname = varname.replace('x', 'z')
        elif varname[-1] == 'z':
            varname = varname.replace('z', 'x')

        self.datafits = self.trans2comm(varname, snap=snap)

        varu = varname.replace('x', '')
        varu = varu.replace('y', '')
        varu = varu.replace('z', '')
        varu = varu.replace('lg', '')
        if (varname in self.varn.keys()) and (varu in self.uni.uni.keys()):
            siunits = self.uni.unisi[varu]/self.uni.uni[varu]
        else:
            siunits = 1.0

        units_title(self)

        if varu == 'ne':
            self.fitsunits = 'm^(-3)'
            siunits = 1e6
        else:
            self.fitsunits = self.unisi_title[varu]

        if varname[:2] == 'lg':
            self.datafits = self.datafits + np.log10(siunits)  # cgs -> SI
        else:
            self.datafits = self.datafits * siunits

        self.xfits = self.x / 1e8
        self.yfits = self.y / 1e8
        self.zfits = self.z / 1e8

        if iz0 != None:
            self.zfits -= self.z[iz0]/1e8

        if z_tau51m == None:
            tau51 = self.trans2comm('tau', snap=snap)
            z_tau51 = np.zeros((self.nx, self.ny))
            for ix in range(0, self.nx):
                for iy in range(0, self.ny):
                    z_tau51[ix, iy] = self.zfits[np.argmin(np.abs(tau51[ix, iy, :]-1.0))]

            z_tau51m = np.mean(z_tau51)

        print(z_tau51m)

        self.dxfits = self.dx / 1e8
        self.dyfits = self.dy / 1e8
        self.dzfits = self.dz / 1e8

        writefits(self, varname, instrument=instrument, name=name,
                  origin=origin, z_tau51m=z_tau51m)


    def set_domain_iiaxis(self, iinum=None, iiaxis='x'):
        """
        Sets iix=iinum and xLength=len(iinum). (x=iiaxis)
        if iinum is a slice, use self.nx (or self.nzb, for x='z') to determine xLength.

        Also, if we end up using a non-None slice, disable stagger.
        TODO: maybe we can leave do_stagger=True?

        Parameters
        ----------
        iinum - slice, int, list, array, or None (default)
            Slice to be taken from get_var quantity in that axis (iiaxis)
            int --> convert to slice(iinum, iinum+1) (to maintain dimensions of output)
            None --> don't change existing self.iix (or iiy or iiz).
                     if it doesn't exist, set it to slice(None).
            To set existing self.iix to slice(None), use iinum=slice(None).
        iiaxis - string
            Axis from which the slice will be taken ('x', 'y', or 'z')

        Returns True if any changes were made, else None.
        """
        iix = 'ii' + iiaxis
        if hasattr(self, iix):
            # if iinum is None or self.iix == iinum, do nothing and return nothing.
            if (iinum is None):
                return None
            elif np.all(iinum == getattr(self, iix)):
                return None

        if iinum is None:
            iinum = slice(None)

        if not np.array_equal(iinum, slice(None)):
            # smash self.variables. Necessary, since we will change the domain size.
            self.variables = {}

        if isinstance(iinum, (int, np.integer)):  # we convert to slice, to maintain dimensions of output.
            iinum = slice(iinum, iinum+1)  # E.g. [0,1,2][slice(1,2)] --> [1]; [0,1,2][1] --> 1

        # set self.iix
        setattr(self, iix, iinum)
        if self.verbose:
            # convert iinum to string that wont be super long (in case iinum is a long list)
            try:
                assert len(iinum) > 20
            except (TypeError, AssertionError):
                iinumprint = iinum
            else:
                iinumprint = 'list with length={:4d}, min={:4d}, max={:4d}, x[1]={:2d}'
                iinumprint = iinumprint.format(len(iinum), min(iinum), max(iinum), iinum[1])
            # print info.
            print('(set_domain) {}: {}'.format(iix, iinumprint),
                  whsp*4, end="\r", flush=True)

        # set self.xLength
        if isinstance(iinum, slice):
            nx = getattr(self, 'n'+iiaxis)
            indSize = len(range(*iinum.indices(nx)))
        else:
            iinum = np.asarray(iinum)
            if iinum.dtype == 'bool':
                indSize = np.sum(iinum)
            else:
                indSize = np.size(iinum)
        setattr(self, iiaxis + 'Length', indSize)

        return True

    def set_domain_iiaxes(self, iix=None, iiy=None, iiz=None, internal=False):
        '''sets iix, iiy, iiz, xLength, yLength, zLength.
        iix: slice, int, list, array, or None (default)
            Slice to be taken from get_var quantity in x axis
            None --> don't change existing self.iix.
                     if self.iix doesn't exist, set it to slice(None).
            To set existing self.iix to slice(None), use iix=slice(None).
        iiy, iiz: similar to iix.
        internal: bool (default: False)
            if internal and self.do_stagger, don't change slices.
            internal=True inside get_var.

        updates x, y, z, dx1d, dy1d, dz1d afterwards, if any domains were changed.
        '''
        if internal and self.do_stagger:
            # we slice at the end, only. For now, set all to slice(None)
            slices = (slice(None), slice(None), slice(None))
        else:
            slices = (iix, iiy, iiz)

        any_domain_changes = False
        for x, iix in zip(AXES, slices):
            domain_changed = self.set_domain_iiaxis(iix, x)
            any_domain_changes = any_domain_changes or domain_changed

        # update x, y, z, dx1d, dy1d, dz1d appropriately.
        #if any_domain_changes:
        #    self.__read_mesh(self.meshfile, firstime=False)

    def write_mesh_file(self, meshfile='untitled_mesh.mesh', u_l=None):
        '''writes mesh to meshfilename.
        mesh will be the mesh implied by self,
        using values for x, y, z, dx1d, dy1d, dz1d, indexed by iix, iiy, iiz.

        u_l: None, or a number
            cgs length units (length [simulation units] * u_l = length [cm]),
                for whoever will be reading the meshfile.
            None -> use length units of self.

        Returns abspath to generated meshfile.
        '''
        if not meshfile.endswith('.mesh'):
            meshfile += '.mesh'
        if u_l is None:
            scaling = 1.0
        else:
            scaling = self.uni.uni['l'] / u_l
        kw_x = {x: getattr(self,    x) * scaling for x in AXES}
        kw_dx = {'d'+x: getattr(self, 'd'+x+'1d') / scaling for x in AXES}
        kw_nx = {'n'+x: getattr(self, x+'Length') for x in AXES}
        kw_mesh = {**kw_x, **kw_nx, **kw_dx}
        Create_new_br_files().write_mesh(**kw_mesh, meshfile=meshfile)
        return os.path.abspath(meshfile)

    write_meshfile = write_mesh_file  # alias


def cross_sect_for_obj(obj=None):
    '''return function which returns Cross_sect with self.obj=obj.
    obj: None (default) or an object
        None -> does nothing; ignore this parameter.
        else -> improve time-efficiency by saving data from cross_tab files
                into memory of obj (save in obj._memory_read_cross_txt).
                Also, use fdir=obj.fdir, unless fdir is entered explicitly.
    '''
    @functools.wraps(Cross_sect)
    def _init_cross_sect(cross_tab=None, fdir=None, *args__Cross_sect, **kw__Cross_sect):
        if fdir is None:
            fdir = getattr(obj, 'fdir', '.')
        return Cross_sect(cross_tab, fdir, *args__Cross_sect, **kw__Cross_sect, obj=obj)
    return _init_cross_sect

## Tools for making cross section table such that colfreq is independent of temperature ##


def constant_colfreq_cross(tg0, Q0, tg=range(1000, 400000, 100), T_to_eV=lambda T: T / 11604):
    '''makes values for constant collision frequency vs temperature cross section table.
    tg0, Q0:
        enforce Q(tg0) = Q0.
    tg: array of values for temperature.
        (recommend: 1000 to 400000, with intervals of 100.)
    T_to_eV: function
        T_to_eV(T) --> value in eV.

    colfreq = consts * Q(tg) * sqrt(tg).
        For constant colfreq:
        Q(tg1) sqrt(tg1) = Q(tg0) sqrt(tg0)

    returns dict of arrays. keys: 'E' (for energy in eV), 'T' (for temperature), 'Q' (for cross)
    '''
    tg = np.asarray(tg)
    E = T_to_eV(tg)
    Q = Q0 * np.sqrt(tg0) / np.sqrt(tg)
    return dict(E=E, T=tg, Q=Q)


def cross_table_str(E, T, Q, comment=''):
    '''make a string for the table for cross sections.
    put comment at top of file if provided.
    '''
    header = ''
    if len(comment) > 0:
        if not comment.startswith(';'):
            comment = ';' + comment
        header += comment + '\n'
    header += '\n'.join(["",
                         "; 1 atomic unit of square distance = 2.80e-17 cm^2",
                         "; 1eV = 11604K",
                         "",
                         "2.80e-17",
                         "",
                         "",
                         ";   E            T          Q11  ",
                         ";  (eV)         (K)        (a.u.)",
                         "",
                         "",
                         ])
    lines = []
    for e, t, q in zip(E, T, Q):
        lines.append('{:.6f}       {:d}       {:.3f}'.format(e, t, q))
    return header + '\n'.join(lines)


def constant_colfreq_cross_table_str(tg0, Q0, **kw):
    '''make a string for a cross section table which will give constant collision frequency (vs tg).'''
    if 'comment' in kw:
        comment = kw.pop('comment')
    else:
        comment = '\n'.join(['; This table provides cross sections such that',
                             '; the collision frequency will be independent of temperature,',
                             '; assuming the functional form colfreq proportional to sqrt(T).',
                             ])
    ccc = constant_colfreq_cross(tg0, Q0, **kw)
    result = cross_table_str(**ccc, comment=comment)
    return result


@file_memory.remember_and_recall('_memory_read_cross_txt', kw_mem=['kelvin'])
def read_cross_txt(filename, firstime=False, kelvin=True):
    ''' Reads IDL-formatted (command style) ascii file into dictionary.
    tg will be converted to Kelvin, unless kelvin==False.
    '''
    li = 0
    params = {}
    # go through the file, add stuff to dictionary
    with open(filename) as fp:
        for line in fp:
            # ignore empty lines and comments
            line = line.strip()
            if len(line) < 1:
                li += 1
                continue
            if line[0] == ';':
                li += 1
                continue
            line = line.split(';')[0].split()
            if (len(line) == 1):
                params['crossunits'] = float(line[0].strip())
                li += 1
                continue
            elif not ('crossunits' in params.keys()):
                print('(WWW) read_cross: line %i is invalid, missing crossunits, file %s' % (li, filename))

            if (len(line) < 2):
                if (firstime):
                    print('(WWW) read_cross: line %i is invalid, skipping, file %s' % (li, filename))
                li += 1
                continue
            # force lowercase because IDL is case-insensitive
            temp = line[0].strip()
            cross = line[2].strip()

            # instead of the insecure 'exec', find out the datatypes
            if ((temp.upper().find('E') >= 0) or (temp.find('.') >= 0)):
                # float type
                temp = float(temp)
            else:
                # int type
                try:
                    temp = int(temp)
                except Exception:
                    if (firstime):
                        print('(WWW) read_cross: could not find datatype in '
                              'line %i, skipping' % li)
                    li += 1
                    continue
            if not ('tg' in params.keys()):
                params['tg'] = temp
            else:
                params['tg'] = np.append(params['tg'], temp)

            if ((cross.upper().find('E') >= 0) or (cross.find('.') >= 0)):
                # float type
                cross = float(cross)
            else:
                # int type
                try:
                    cross = int(cross)
                except Exception:
                    if (firstime):
                        print('(WWW) read_cross: could not find datatype in '
                              'line %i, skipping' % li)
                    li += 1
                    continue
            if not ('el' in params.keys()):
                params['el'] = cross
            else:
                params['el'] = np.append(params['el'], cross)

            if len(line) > 2:
                cross = line[2].strip()

                if ((cross.upper().find('E') >= 0) or (cross.find('.') >= 0)):
                    # float type
                    cross = float(cross)
                else:
                    # int type
                    try:
                        cross = int(cross)
                    except Exception:
                        if (firstime):
                            print('(WWW) read_cross: could not find datatype'
                                  'in line %i, skipping' % li)
                        li += 1
                        continue
                if not ('mt' in params.keys()):
                    params['mt'] = cross
                else:
                    params['mt'] = np.append(params['mt'], cross)

            if len(line) > 3:
                cross = line[3].strip()

                if ((cross.upper().find('E') >= 0) or (cross.find('.') >= 0)):
                    # float type
                    cross = float(cross)
                else:
                    # int type
                    try:
                        cross = int(cross)
                    except Exception:
                        if (firstime):
                            print('(WWW) read_cross: could not find datatype'
                                  'in line %i, skipping' % li)
                        li += 1
                        continue
                if not hasattr(params, 'vi'):
                    params['vi'] = cross
                else:
                    params['vi'] = np.append(params['vi'], cross)

            if len(line) > 4:
                cross = line[4].strip()

                if ((cross.upper().find('E') >= 0) or (cross.find('.') >= 0)):
                    # float type
                    cross = float(cross)
                else:
                    # int type
                    try:
                        cross = int(cross)
                    except Exception:
                        if (firstime):
                            print('(WWW) read_cross: could not find datatype'
                                  'in line %i, skipping' % li)
                        li += 1
                        continue
                if not hasattr(params, 'se'):
                    params['se'] = cross
                else:
                    params['se'] = np.append(params['se'], cross)
            li += 1

    # convert to kelvin
    if kelvin:
        params['tg'] *= Muram_units(verbose=False).ev_to_k

    return params


def calc_grph(abundances, atomic_weights):
    """
    Calculate grams per hydrogen atom, given a mix of abundances
    and respective atomic weights.

    Parameters
    ----------
    abundances : 1D array
        Element abundances relative to hydrogen in log scale,
        where hydrogen is defined as 12.
    atomic_weights : 1D array
        Atomic weights for each element in atomic mass units.

    Returns
    -------
    grph : float
        Grams per hydrogen atom.
    """
    from astropy.constants import u as amu
    linear_abundances = 10.**(abundances - 12.)
    masses = atomic_weights * amu.to_value('g')
    return np.sum(linear_abundances * masses)


def subs2grph(subsfile):
    """
    Extract abundances and atomic masses from subs.dat, and calculate
    the number of grams per hydrogen atom.

    Parameters
    ----------
    subsfile : str
        File name of subs.dat.

    Returns
    -------
    grph : float
        Grams per hydrogen atom.
    """
    f = open(subsfile, 'r')
    nspecies = np.fromfile(f, count=1, sep=' ', dtype='i')[0]
    f.readline()  # second line not important
    ab = np.fromfile(f, count=nspecies, sep=' ', dtype='f')
    am = np.fromfile(f, count=nspecies, sep=' ', dtype='f')
    f.close()
    return calc_grph(ab, am)


def find_first_match(name, path, incl_path=False):
    '''
    This will find the first match,
    name : string, e.g., 'patern*'
    incl_root: boolean, if true will add full path, otherwise, the name.
    path : sring, e.g., '.'
    '''
    originalpath = os.getcwd()
    os.chdir(path)
    for file in glob(name):
        if incl_path:
            os.chdir(originalpath)
            return os.path.join(path, file)
        else:
            os.chdir(originalpath)
            return file
    os.chdir(originalpath)


class Cross_sect:
    """
    Reads data from Bifrost collisional cross section tables.

    Parameters
    ----------
    cross_tab - string or array of strings
        File names of the ascii cross table files.
    fdir - string, optional
        Directory where simulation files are. Must be a real path.
    verbose - bool, optional
        If True, will print out more diagnostic messages
    dtype - string, optional
        Data type for reading variables. Default is 32 bit float.
    kelvin - bool (default True)
        Whether to load data in Kelvin. (uses eV otherwise)

    Examples
    --------
        a = cross_sect(['h-h-data2.txt','h-h2-data.txt'], fdir="/data/cb24bih")

    """

    def __init__(self, cross_tab=None, fdir=os.curdir, dtype='f4', verbose=None, kelvin=True, obj=None):
        '''
        Loads cross section tables and calculates collision frequencies and
        ambipolar diffusion.

        parameters:
        cross_tab: None or list of strings
            None -> use default cross tab list of strings.
            else -> treat each string as the name of a cross tab file.
        fdir: str (default '.')
            directory of files (prepend to each filename in cross_tab).
        dtype: default 'f4'
            sets self.dtype. aside from that, internally does NOTHING.
        verbose: None (default) or bool.
            controls verbosity. presently, internally does NOTHING.
            if None, use obj.verbose if possible, else use False (default)
        kelvin - bool (default True)
            Whether to load data in Kelvin. (uses eV otherwise)
        obj: None (default) or an object
            None -> does nothing; ignore this parameter.
            else -> improve time-efficiency by saving data from cross_tab files
                    into memory of obj (save in obj._memory_read_cross_txt).
        '''
        self.fdir = fdir
        self.dtype = dtype
        if verbose is None:
            verbose = False if obj is None else getattr(obj, 'verbose', False)
        self.verbose = verbose
        self.kelvin = kelvin
        self.units = {True: 'K', False: 'eV'}[self.kelvin]
        # save pointer to obj. Use weakref to help ensure we don't create a circular reference.
        self.obj = (lambda: None) if (obj is None) else weakref.ref(obj)  # self.obj() returns obj.
        # read table file and calculate parameters
        if cross_tab is None:
            cross_tab = ['h-h-data2.txt', 'h-h2-data.txt', 'he-he.txt',
                         'e-h.txt', 'e-he.txt', 'h2_molecule_bc.txt',
                         'h2_molecule_pj.txt', 'p-h-elast.txt', 'p-he.txt',
                         'proton-h2-data.txt']
        self._cross_tab_strs = cross_tab
        self.cross_tab_list = {}
        for i, cross_txt in enumerate(cross_tab):
            self.cross_tab_list[i] = os.path.join(fdir, cross_txt)

        # load table(s)
        self.load_cross_tables(firstime=True)

    def load_cross_tables(self, firstime=False):
        '''
        Collects the information in the cross table files.
        '''
        self.cross_tab = dict()
        for itab in range(len(self.cross_tab_list)):
            self.cross_tab[itab] = read_cross_txt(self.cross_tab_list[itab], firstime=firstime,
                                                  obj=self.obj(), kelvin=self.kelvin)

    def tab_interp(self, tg, itab=0, out='el', order=1):
        ''' Interpolates the cross section tables in the simulated domain.
            IN:
                tg  : Temperature [K]
                order: interpolation order (1: linear, 3: cubic)
            OUT:
                'se'  : Spin exchange cross section [a.u.]
                'el'  : Integral Elastic cross section [a.u.]
                'mt'  : momentum transfer cross section [a.u.]
                'vi'  : viscosity cross section [a.u.]
        '''

        if out in ['se el vi mt'.split()] and not self.load_cross_tables:
            raise ValueError("(EEE) tab_interp: EOS table not loaded!")

        finterp = interpolate.interp1d(np.log(self.cross_tab[itab]['tg']),
                                       self.cross_tab[itab][out])
        tgreg = np.array(tg, copy=True)
        max_temp = np.max(self.cross_tab[itab]['tg'])
        tgreg[tg > max_temp] = max_temp
        min_temp = np.min(self.cross_tab[itab]['tg'])
        tgreg[tg < min_temp] = min_temp

        return finterp(np.log(tgreg))

    def __call__(self, tg, *args, **kwargs):
        '''alias for self.tab_interp.'''
        return self.tab_interp(tg, *args, **kwargs)

    def __repr__(self):
        return '{} == {}'.format(object.__repr__(self), str(self))

    def __str__(self):
        return "Cross_sect(cross_tab={}, fdir='{}')".format(self._cross_tab_strs, self.fdir)


class Muram_units(units.HelitaUnits):

    def __init__(self, filename=None, base_units=None, verbose=False,**kw__super_init):
        '''
        Units and constants in cgs
        '''
        #self.uni = {}
        #self.verbose = verbose
        #self.uni['tg'] = 1.0  # K
        #self.uni['l'] = 1.0  # to cm
        #self.uni['u_l'] = 1.0  # to cm
        #print(self.uni['u_l'])
        #self.uni['rho'] = 1.0  # g cm^-3
        #self.uni['u'] = 1.0  # cm/s
        #self.uni['b'] = np.sqrt(4.0*np.pi)  # convert to Gauss
        #self.uni['t'] = 1.0  # seconds
        #self.uni['j'] = 1.0  # current density
        '''get units from file (by reading values of u_l, u_t, u_r, gamma).

        filename: str; name of file. Default 'mhd.in'
        fdir: str; directory of file. Default './'
        verbose: True (default) or False
            True -> if we use default value for a base unit because
                    we can't find its value otherwise, print warning.
        base_units: None (default), dict, or list
            None -> ignore this keyword.
            dict -> if contains any of the keys: u_l, u_t, u_r, gamma,
                    initialize the corresponding unit to the value found.
                    if base_units contains ALL of those keys, IGNORE file.
            list -> provides value for u_l, u_t, u_r, gamma; in that order.
        '''
        DEFAULT_UNITS = dict(u_l=1., u_t=1., u_r=1.0, gamma=1.667)
        base_to_use = dict()  # << here we will put the u_l, u_t, u_r, gamma to actually use.
        _n_base_set = 0  # number of base units set (i.e. assigned in base_to_use)

        # setup units from base_units, if applicable
        if base_units is not None:
            try:
                base_units.items()
            except AttributeError:  # base_units is a list
                for i, val in enumerate(base_units):
                    base_to_use[self.BASE_UNITS[i]] = val
                    _n_base_set += 1
            else:
                for key, val in base_units.items():
                    if key in DEFAULT_UNITS.keys():
                        base_to_use[key] = val
                        _n_base_set += 1
                    elif verbose:
                        print(('(WWW) the key {} is not a base unit',
                              ' so it was ignored').format(key))

        # setup units from file (or defaults), if still necessary.
        if _n_base_set != len(DEFAULT_UNITS):
            if filename is None:
                file_exists = False
            else:
                file = os.path.join(fdir, filename)
                file_exists = os.path.isfile(file)
            if file_exists:
                # file exists -> set units using file.
                self.params = read_idl_ascii(file, firstime=True)

                def setup_unit(key):
                    if base_to_use.get(key, None) is not None:
                        return
                    # else:
                    try:
                        value = self.params[key]
                    except Exception:
                        value = DEFAULT_UNITS[key]
                        if verbose:
                            printstr = ("(WWW) the file '{file}' does not contain '{unit}'. "
                                        "Default Solar Bifrost {unit}={value} has been selected.")
                            print(printstr.format(file=file, unit=key, value=value))
                    base_to_use[key] = value

                for unit in DEFAULT_UNITS.keys():
                    setup_unit(unit)
            else:
                # file does not exist -> setup default units.
                units_to_set = {unit: DEFAULT_UNITS[unit] for unit in DEFAULT_UNITS.keys()
                                if getattr(self, unit, None) is None}
                if verbose:
                    print("(WWW) selected file '{file}' is not available.".format(file=filename),
                          "Setting the following Default Solar Bifrost units: ", units_to_set)
                for key, value in units_to_set.items():
                    base_to_use[key] = value

        # initialize using instructions from HelitaUnits (see helita.sim.units.py)
        super().__init__(**base_to_use, verbose=verbose, **kw__super_init)


        # Units and constants in SI
        convertcsgsi(self)

        globalvars(self)


class Create_new_br_files:
    def write_mesh(self, x=None, y=None, z=None, nx=None, ny=None, nz=None,
                   dx=None, dy=None, dz=None, meshfile="newmesh.mesh"):
        """
        Writes mesh to ascii file.

        The meshfile units are simulation units for length (or 1/length, for derivatives).
        """
        def __xxdn(f):
            '''
            f is centered on (i-.5,j,k)
            '''
            nx = len(f)
            d = -5. / 2048
            c = 49. / 2048
            b = -245. / 2048
            a = .5 - b - c - d
            x = (a * (f + np.roll(f, 1)) +
                 b * (np.roll(f, -1) + np.roll(f, 2)) +
                 c * (np.roll(f, -2) + np.roll(f, 3)) +
                 d * (np.roll(f, -3) + np.roll(f, 4)))
            for i in range(0, 4):
                x[i] = x[4] - (4 - i) * (x[5] - x[4])
            for i in range(1, 4):
                x[nx - i] = x[nx - 4] + i * (x[nx - 4] - x[nx - 5])

            x[nx-3:] = x[nx-3:][::-1]  # fixes order in the tail of x
            return x

        def __ddxxup(f, dx=None):
            '''
            X partial up derivative
            '''
            if dx is None:
                dx = 1.
            nx = len(f)
            d = -75. / 107520. / dx
            c = 1029 / 107520. / dx
            b = -8575 / 107520. / dx
            a = 1. / dx - 3 * b - 5 * c - 7 * d
            x = (a * (np.roll(f, -1) - f) +
                 b * (np.roll(f, -2) - np.roll(f, 1)) +
                 c * (np.roll(f, -3) - np.roll(f, 2)) +
                 d * (np.roll(f, -4) - np.roll(f, 3)))
            x[:3] = x[3]
            for i in range(1, 5):
                x[nx - i] = x[nx - 5]
            return x

        def __ddxxdn(f, dx=None):
            '''
            X partial down derivative
            '''
            if dx is None:
                dx = 1.
            nx = len(f)
            d = -75. / 107520. / dx
            c = 1029 / 107520. / dx
            b = -8575 / 107520. / dx
            a = 1. / dx - 3 * b - 5 * c - 7 * d
            x = (a * (f - np.roll(f, 1)) +
                 b * (np.roll(f, -1) - np.roll(f, 2)) +
                 c * (np.roll(f, -2) - np.roll(f, 3)) +
                 d * (np.roll(f, -3) - np.roll(f, 4)))
            x[:4] = x[4]
            for i in range(1, 4):
                x[nx - i] = x[nx - 4]
            return x

        f = open(meshfile, 'w')

        for p in ['x', 'y', 'z']:
            setattr(self, p, locals()[p])
            if (getattr(self, p) is None):
                setattr(self, 'n' + p, locals()['n' + p])
                setattr(self, 'd' + p, locals()['d' + p])
                setattr(self, p, np.linspace(0,
                                             getattr(self, 'n' + p) *
                                             getattr(self, 'd' + p),
                                             getattr(self, 'n' + p)))
            else:
                if (len(locals()[p]) < 1):
                    raise ValueError("(EEE): "+p+" axis has length zero")
                setattr(self, 'n' + p, len(locals()[p]))
            if getattr(self, 'n' + p) > 1:
                xmdn = __xxdn(getattr(self, p))
                dxidxup = __ddxxup(getattr(self, p))
                dxidxdn = __ddxxdn(getattr(self, p))
            else:
                xmdn = getattr(self, p)
                dxidxup = np.array([1.0])
                dxidxdn = np.array([1.0])
            f.write(str(getattr(self, 'n' + p)) + "\n")
            f.write(" ".join(map("{:.5f}".format, getattr(self, p))) + "\n")
            f.write(" ".join(map("{:.5f}".format, xmdn)) + "\n")
            f.write(" ".join(map("{:.5f}".format, 1.0/dxidxup)) + "\n")
            f.write(" ".join(map("{:.5f}".format, 1.0/dxidxdn)) + "\n")
        f.close()
