"""
Set of tools to interface with output and input from simulations
and radiative transfer codes. Also includes routines for working
with synthetic spectra.
"""
from .tools import (
    # defaults
    IMPORT_FAILURE_WARNINGS,
    # writing snaps
    writefits, allsnap2fits, inttostring,
    # units
    units_title, convertcsgsi, globalvars,
    # API
    apply, is_integer, format_docstring,
    NO_VALUE,
    # coordinate transformations
    polar2cartesian, cartesian2polar, refine,
    # restore attrs
    maintain_attrs, MaintainingAttrs, maintaining_attrs,
    UsingAttrs, using_attrs, with_attrs,
    EnterDir, RememberDir, EnterDirectory,
    with_dir, withdir,
    maintain_cwd, maintain_directory, maintain_dir,
    # info about arrays
    stats, print_stats,
    finite_op, finite_min, finite_mean, finite_max, finite_std, finite_median,
    # manipulating arrays
    slicer_at_ax,
    # strings
    pretty_nbytes,
    # imports
    ImportFailedError, ImportFailed,
    import_relative, try_import_relative,
    boring_decorator,
    # vector rotations
    rotation_align, rotation_apply, RotationManager3D,
    # plotting
    centered_extent1D, centered_extent, extent,
    make_cax, make_colorbar_axis, make_colorbar_axes,
    # custom versions of builtins
    GenericDict, GenericDict_with_equals,
)

# try importing all the modules inside helita.sim
_modules = ['aux_compare', 'bifrost', 'document_vars',
            'ebysus', 'fake_ebysus_data',
            'file_memory', 'fluid_tools',
            'load_arithmetic_quantities', 'load_fromfile_quantities',
            'load_noeos_quantities', 'load_quantities',
            'stagger', 'units',
            ]
_locals = locals()
_globals = globals()
for _module in _modules:
    _locals[_module] = try_import_relative('.'+_module, _globals)

# also set some aliases to modules
_module_aliases = {
    'aux_compare': 'axc',
    'bifrost': 'bf',
    'ebysus': 'eb',
    'fake_ebysus_data': 'feb',
    'load_arithmetic_quantities': 'laq',
    'load_fromfile_quantities': 'lfq',
    'load_noeos_quantities': 'lnq',
    'load_quantities': 'lq',
}
for _module, _alias in _module_aliases.items():
    _locals[_alias] = _locals[_module]
