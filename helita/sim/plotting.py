"""
Plotting for helita data objects (e.g. BifrostData, EbysusData)

attach methods directly to those objects, for convenience.
"""

import numpy as np

from .tools import (
    ImportFailed,
    NO_VALUE,
    centered_extent1D, centered_extent, make_cax,
)

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = ImportFailed('matplotlib.pyplot')


class Plottable3D():
    '''lots of helpful methods for plotting data from a 3D helita data object.
    Intended to be subclassed (e.g. BifrostData inherit from Plottable3D),
    rather than instantiated directly.
    Assumes the existence of many properties available to BifrostData.
    '''
    # [TODO] make a more generic HelitaData3D, then make Plottable3D a subclass of that.

    def _get_plottable_var_and_vals(self, var_or_vals):
        '''returns (varname, var_or_vals as an ndarray)
        if var is a string, returns (var_or_vals, self(var_or_vals))
        otherwise, returns (None, np.asanyarray(var_or_vals))
        '''
        if isinstance(var_or_vals, str):
            var = var_or_vals
            vals = self(var)
        else:
            var = None  # unknown var name.
            vals = np.asanyarray(var_or_vals)
        return (var, vals)

    def imshow(self, var_or_vals, axes=None, *, at_x=None, at_y=None, at_z=None,
               log=False, usi_key=None, ucgs_key=None,
               coord_units='si', xcoord_transform=None, ycoord_transform=None,
               colorbar=True, cbar_label=None, kw_cbar=dict(), sca_cbar=False,
               origin=NO_VALUE, extent=NO_VALUE, flipz=False,
               interpolation='none',
               **kw__imshow):
        '''plot var.T as a 2D image.
        var_or_vals: str or ndarray
            if str, use self(var_or_vals).
            if 3D...
                if exactly one of the dimensions has length 1, infer the axes based on that.
                    e.g. shape (100, 1, 50) --> plot along the x & z axes; use at_y=0.
                if none of the dimensions have length 1, must provide axes, at_x, at_y, or at_z.
            if 2D...
                must provide axes.
        axes: None, or str or tuple with length 2, contents 'x', 'y', 'z', 0, 1, or 2.
            which axes to plot. E.g. 'xz' or (0, 2) or (0, 'z').
            None --> infer from at_x, at_y, at_z, or shape of array.
            length 2 --> use axes[0] as the x axis on the plot; axes[1] as the y axis.
        at_x, at_y, at_z: None or int
            index along this axis to choose. provide at most one of these values.
            E.g., if at_y=7, then the array to plot will be var_or_vals[:, 7, :].
        log: bool, default False
            if True, take log10(abs(vals)) before plotting.
        usi_key: None or str
            if provided, convert to si via val=val*self.uni(usi_key, 'si', self.units_output)
        ucgs_key: None or str
            if provided, convert to cgs via val=val*self.uni(ucgs_key, 'cgs', self.units_output)
        coord_units: str
            units for coords of axes. 'si', 'cgs', or 'simu'.
        xcoord_transform, ycoord_transform: None or callable of one argument
            if provided, apply to xcoord and ycoord before plotting.
            xcoord and ycoord correspond to the plot x-axis & y-axis,
                e.g. if axes='xz' then xcoord <--> 'x'; ycoord <--> 'z'.
            if provided, will not include units in the label for that coordinate.
                (you should label it separately, e.g. plt.xlabel(...))
        colorbar: bool, default True
            whether to make a colorbar as well.
            if True, will use tools.make_cax to make the colorbar axis
        cbar_label: None or str
            if provided and colorbar=True, label the colorbar with this label
        kw_cbar: dict
            pass these kwargs to plt.colorbar()
        sca_cbar: bool, default False
            whether to set current axis to the colorbar axis.
            if False, instead ensure current axis is the image axis.
        flipz: bool, default False
            if True, "flip z axis" (only applies if one of the axes is 'z' (or 2))
            This accounts for Bifrost z coordinate being upside-down & negative.
                It changes the default extent to use -zcoords[::-1], and origin='upper'.
        origin: NO_VALUE, None, or str
            if NO_VALUE, use default of 'lower' if flipz=False, else 'upper'.
            otherwise, pass this value directly to plt.imshow.
        extent: NO_VALUE, None, or tuple
            if NO_VALUE, use default of determining extent from coordinates (& value of flipz).
            otherwise, pass this value directly to plt.imshow.

        additional kwargs go to plt.imshow().
        returns (result of plt.imshow(...), result of plt.colorbar()).
            (if not colorbar, instead just return result of plt.imshow().)
        '''
        # figure out the array & axes to use
        var, vals = self._get_plottable_var_and_vals(var_or_vals)
        array, axes = _get_plottable_array_and_axes(vals, axes=axes, at_x=at_x, at_y=at_y, at_z=at_z, _ndim=2)
        if usi_key is not None and ucgs_key is not None:
            raise ValueError("cannot provide BOTH usi_key and ucgs_key")
        if usi_key is not None:
            array = array * self.uni(usi_key, 'si', self.units_output)
        if ucgs_key is not None:
            array = array * self.uni(ucgs_key, 'cgs', self.units_output)
        if log:
            array = np.log10(np.abs(array))
        array_to_plot = array if (axes[0] > axes[1]) else array.T  # get the orientation correct.
        # get the coordinates
        xcoord, ycoord = self.get_coords(units=coord_units, axes=axes)
        if xcoord_transform is not None:
            xcoord = xcoord_transform(xcoord)
        if ycoord_transform is not None:
            ycoord = ycoord_transform(ycoord)
        if flipz and (2 in axes):
            if axes[0] == 2:
                xcoord = -xcoord[::-1]
            else:  # axes[1] == 2
                ycoord = -ycoord[::-1]
        if extent is NO_VALUE:
            extent = centered_extent(xcoord, ycoord, ndim0_ok=True)
        if origin is NO_VALUE:
            origin = 'upper' if flipz else 'lower'
        # actually plot the image
        result = plt.imshow(array_to_plot, extent=extent,
                            origin=origin, interpolation=interpolation,
                            **kw__imshow)
        image_axis = plt.gca()
        # label the image
        xlabel = f'{_axis_to_str(axes[0])}' + (f' [{coord_units}]' if xcoord_transform is None else '')
        ylabel = f'{_axis_to_str(axes[1])}' + (f' [{coord_units}]' if ycoord_transform is None else '')
        plt.xlabel(xlabel); plt.ylabel(ylabel)
        if usi_key is not None:
            varunits = 'si'
        elif ucgs_key is not None:
            varunits = 'cgs'
        else:
            varunits = getattr(self, 'units_output', None)
        if var is None:
            var = 'var=???'
        title = var if varunits is None else f'{var} [{varunits}]'
        if log:
            title = f'log10(| {title} |)'
        plt.title(title)
        # handle the colorbar
        if colorbar:
            cax = make_cax()
            cbar = plt.colorbar(cax=cax, label=cbar_label, **kw_cbar)
            if not sca_cbar:
                plt.sca(image_axis)  # set current axis to image_axis instead of colorbar.
            return result, cbar
        else:
            return result


''' --------------------------- axis selection tools --------------------------- '''
def _axis_to_int(axis):
    '''convert axis (str or int) into an integer
    axis can be 'x', 'y', 'z', 0, 1, or 2.
    result will be 0, 1, or 2.
    '''
    return int({'x': 0, 'y': 1, 'z': 2}.get(axis, axis))

def _axis_to_str(axis):
    '''convert axis (str or int) into a string
    axis can be 'x', 'y', 'z', 0, 1, or 2.
    result will be 'x', 'y', or 'z'.
    '''
    return str({0: 'x', 1: 'y', 2: 'z'}.get(axis, axis))

def _axes_to_ints(axes):
    '''convert axes to tuple of ints'''
    return tuple(int(_axis_to_int(x)) for x in axes)

def _unused_axes(axes):
    '''return tuple of ints from 0, 1, 2 for axes missing from axes.'''
    return tuple(set((0,1,2)) - set(_axes_to_ints(axes)))

def _get_plottable_axes(axes=None, *, at_x=None, at_y=None, at_z=None, ndim=None):
    '''returns (tuple of integers indicating implied axes, tuple for indexing a 3D array).
    if ndim is provided, raise ValueError unless the result implies an array with ndim=ndim.
    '''
    if axes is not None:
        # ensure no conflicts between axes & at_{x}
        axes = _axes_to_ints(axes)
        if 0 in axes and at_x is not None: raise ValueError(f'incompatible axes & at_x: {axes}, {at_x}')
        if 1 in axes and at_y is not None: raise ValueError(f'incompatible axes & at_y: {axes}, {at_y}')
        if 2 in axes and at_z is not None: raise ValueError(f'incompatible axes & at_z: {axes}, {at_z}')
        # default at_{x} = 0
        axes_unused = _unused_axes(axes)
        if 0 in axes_unused and at_x is None: at_x = 0
        if 1 in axes_unused and at_y is None: at_y = 0
        if 2 in axes_unused and at_z is None: at_z = 0
    else:
        # determine which axes to use based on the at_{x} provided
        axes = []
        if at_x is None: axes.append(0)
        if at_y is None: axes.append(1)
        if at_z is None: axes.append(2)
        axes = tuple(axes)
    # ndim check
    if ndim is not None and len(axes) != ndim:
        raise ValueError(f'ndim={ndim} incompatible with axes={axes}')
    # slices calculation
    slices = []
    slices.append(slice(None) if at_x is None else at_x)
    slices.append(slice(None) if at_y is None else at_y)
    slices.append(slice(None) if at_z is None else at_z)
    slices = tuple(slices)
    return (axes, slices)

def _get_plottable_array_and_axes(array, axes=None, *, at_x=None, at_y=None, at_z=None, _ndim=None):
    '''returns (array indexed appropriately, tuple of integers indicating implied axes).
    raise ValueError if inputs are incompatible.

    if array is less than 3D:
        at_x, at_y, or at_z cannot be used.
        axes must be provided, and have length equal to array.ndim
        if _ndim is provided, _ndim must be equal to array.ndim
    if array.ndim >= 3D:
        use axes and at_x, at_y, at_z to determine which axes to use.
        if those are all None, and _ndim < 3, look for dimensions with size 1, in array.shape[:3].
    '''
    array = np.asanyarray(array)
    shape = array.shape
    if array.ndim < 3:
        if at_x is not None or at_y is not None or at_z is not None:
            raise ValueError(f'at_x, at_y, or at_z provided, but array.ndim={array.ndim} < 3')
        if axes is None:
            raise ValueError(f'axes must be provided for array.ndim={array.ndim} < 3')
        if len(axes) != array.ndim:
            raise ValueError(f'axes={axes} incompatible with array.ndim={array.ndim}')
        if _ndim is not None and _ndim != array.ndim:
            raise ValueError(f'_ndim={_ndim} incompatible with array.ndim={array.ndim}')
        axes, slices = _get_plottable_axes(axes=axes)
        slices_nd = slices[:array.ndim]
        return (array[slices], axes)
    # else, array.ndim >= 3.
    if (_ndim < 3) and (axes is None) and (at_x is None) and (at_y is None) and (at_z is None):
        # try to infer axes from array.shape
        axes = []
        if shape[0] != 1: axes.append(0)
        if shape[1] != 1: axes.append(1)
        if shape[2] != 1: axes.append(2)
        axes = tuple(axes)
        if len(axes) == _ndim:
            axes, slices = _get_plottable_axes(axes=axes, ndim=_ndim)
            return (array[slices], axes)
        else:
            raise ValueError(f'cannot infer axes from array.shape={shape} and _ndim={_ndim}')
    # else, axes, at_x, at_y, or at_z are provided
    axes, slices = _get_plottable_axes(axes=axes, at_x=at_x, at_y=at_y, at_z=at_z, ndim=_ndim)
    return (array[slices], axes)
