""" drivers for coordinate scans
"""

import os
import itertools
import numpy
import automol
import autofile
from autofile import fs
import mess_io
from lib.submission import run_script
from lib.submission import DEFAULT_SCRIPT_DCT


# FUNCTIONS TO SET UP TORSION NAME LISTS
def tors_name_prep(spc_dct_i, cnf_fs, min_cnf_locs, tors_model):
    """ Obtain torsion names through various means
    """

    if tors_model in ('1dhr', 'mdhr', 'tau'):
        run_tors_names = ()
        if 'tors_names' in spc_dct_i:
            run_tors_names = names_from_dct(spc_dct_i, tors_model)
            tloc = 'dct'
        if not run_tors_names:
            run_tors_names = names_from_filesys(
                cnf_fs, min_cnf_locs, tors_model)
            tloc = 'fs'
        if not run_tors_names and tors_model == 'tau':
            geo = cnf_fs[-1].file.geometry.read(min_cnf_locs)
            run_tors_names = names_from_geo(
                geo, tors_model, saddle=False)
            tloc = 'geo'
        if not run_tors_names:
            tloc = None
    else:
        tloc = None
        run_tors_names = ()

    if tloc is not None:
        if tloc == 'dct':
            print(' - Reading tors names from user input...')
        elif tloc == 'fs':
            print(' - Reading tors names from the filesystem...')
        elif tloc == 'geo':
            print(' - Obtaining tors names from the geometry...')

    return run_tors_names


def names_from_geo(geo, ndim_tors, saddle=False):
    """ Build the tors name list from a geom
    """
    if not saddle:
        tors_names = [
            [name]
            for name in automol.geom.zmatrix_torsion_coordinate_names(geo)
        ]
        if ndim_tors in ('mdhr', 'mdhrv'):
            tors_names = [[tors
                           for rotor in tors_names
                           for tors in rotor]]
        tors_names = tuple(tuple(x) for x in tors_names)
    else:
        tors_names = tuple()

    return tors_names


def names_from_dct(spc_dct_i, ndim_tors):
    """ Build the tors name list from a dictionary
    """

    # Read names from dct
    inp_tors_names, amech_ts_tors_names = (), ()
    if 'tors_names' in spc_dct_i:
        inp_tors_names = spc_dct_i['tors_names']
        inp_tors_names = tuple(tuple(x) for x in inp_tors_names)
    if 'amech_ts_tors_names' in spc_dct_i:
        amech_ts_tors_names = spc_dct_i['amech_ts_tors_names']
        if ndim_tors == '1dhr':
            amech_ts_tors_names = [[name] for name in amech_ts_tors_names]
        else:
            amech_ts_tors_names = [amech_ts_tors_names]
        amech_ts_tors_names = tuple(tuple(x) for x in amech_ts_tors_names)

    # Set the run tors names
    if inp_tors_names:
        tors_names = inp_tors_names
        print('Using tors names defined by user...')
    elif amech_ts_tors_names:
        tors_names = amech_ts_tors_names
        print('Using tors names generated by AutoMech...')
    else:
        tors_names = ()

    return tors_names, amech_ts_tors_names


def names_from_filesys(tors_cnf_fs, tors_min_cnf_locs, tors_model):
    """ Read out the torsional names from the filesystem
    """

    if tors_min_cnf_locs is not None:

        # Set zma filesys
        zma_fs = fs.manager(tors_cnf_fs[-1].path(tors_min_cnf_locs), 'ZMATRIX')
        zma_path = zma_fs[-1].path([0])

        scans_dir = os.path.join(zma_path, 'SCANS')
        if os.path.exists(scans_dir):
            scan_names = os.listdir(scans_dir)
            tors_names = [name for name in scan_names
                          if 'D' in name]
            if tors_model in ('1dhr', 'tau'):
                tors_names = [name for name in tors_names
                              if '_' not in name]
                tors_names = [[name] for name in tors_names]
            elif tors_model == 'mdhr':
                tors_names = [name for name in tors_names
                              if '_' in name]
                tors_names = [names.split('_') for names in tors_names]
                if not tors_names:
                    tors_names = [name for name in scan_names
                                  if '_' not in name]
                    tors_names = [[name] for name in tors_names]
            tors_names = tuple(tuple(x) for x in tors_names)
        else:
            print('No tors in save filesys')
            tors_names = tuple()
    else:
        print('No min cnf for tors filesys')
        tors_names = tuple()

    # if saddle:
    #     tors_names = spc_dct_i['amech_ts_tors_names']
    # else:
    #     if tors_cnf_save_fs[0].file.info.exists():
    #         inf_obj_s = tors_cnf_save_fs[0].file.info.read()
    #         tors_ranges = inf_obj_s.tors_ranges
    #         tors_ranges = autofile.info.dict_(tors_ranges)
    #         tors_names = list(tors_ranges.keys())

    #     else:
    #         tors_names = None
    #         print('No inf obj to identify torsional angles')

    return tors_names


# FUNCTIONS USED TO BUILD LSTS OF TORSIONS OF ANY DIMENSIONALITY
def hr_prep(zma, tors_name_grps, scan_increment=30.0, tors_model='1dhr',
            frm_bnd_keys=(), brk_bnd_keys=()):
    """ set-up the hr for different rotor combinations
        tors_names = [ ['D1'], ['D2', 'D3'], ['D4'] ]
    """

    # Get the tors names if thery have not already been supplied
    val_dct = automol.zmatrix.values(zma)

    # Deal with the dimensionality of the rotors
    if tors_model in ('mdhr', 'mdhrv'):
        tors_name_grps = mdhr_prep(zma, tors_name_grps)

    # Build the grids corresponding to the torsions
    tors_grids, tors_sym_nums = [], []
    for tors_names in tors_name_grps:
        tors_linspaces = automol.zmatrix.torsional_scan_linspaces(
            zma, tors_names, scan_increment, frm_bnd_key=frm_bnd_keys,
            brk_bnd_key=brk_bnd_keys)
        tors_grids.append(
            [numpy.linspace(*linspace) + val_dct[name]
             for name, linspace in zip(tors_names, tors_linspaces)]
        )
        tors_sym_nums.append(
            automol.zmatrix.torsional_symmetry_numbers(
                zma, tors_names,
                frm_bnd_key=frm_bnd_keys, brk_bnd_key=brk_bnd_keys)
        )

    return tors_name_grps, tors_grids, tors_sym_nums


def mdhr_prep(zma, run_tors_names):
    """ Handle cases where the MDHR
    """

    # Figure out set of torsions are to be used: defined or AMech generated
    rotor_lst = run_tors_names

    # Check the dimensionality of each rotor to see if they are greater than 4
    # Call a function to reduce large rotors
    final_rotor_lst = []
    for rotor in rotor_lst:
        if len(rotor) > 4:
            for reduced_rotor in reduce_rotor_dimensionality(zma, rotor):
                final_rotor_lst.append(reduced_rotor)
        else:
            final_rotor_lst.append(rotor)

    return final_rotor_lst


def reduce_rotor_dimensionality(zma, rotor):
    """ For rotors with a dimensionality greater than 4, try and take them out
    """

    # Find the methyl rotors for that are a part of the MDHR
    reduced_rotor_lst = []
    methyl_rotors = []
    for tors in rotor:
        # If a methyl rotor add to methyl rotor list, or add to reduced lst
        if is_methyl_rotor(zma, rotor):   # Add arguments when ID methyls
            methyl_rotors.append(zma, tors)
        else:
            reduced_rotor_lst.append(tors)

    # Add each of methyl rotors, if any exist
    if methyl_rotors:
        for methyl_rotor in methyl_rotors:
            reduced_rotor_lst.append(methyl_rotor)

    # Check new dimensionality of list; if still high, flatten to lst of 1DHRs
    if len(reduced_rotor_lst) > 4:
        reduced_rotor_lst = [tors
                             for rotor in reduced_rotor_lst
                             for tors in rotor]

    return reduced_rotor_lst


def is_methyl_rotor(zma, rotor):
    """ Check if methyl rotor
    """
    raise NotImplementedError(zma, rotor)


# Building constraints
def build_constraint_dct(zma, const_names, scan_names=()):
    """ Build a dictionary of constraints
    """

    print('const_names', const_names)
    print('scan_names', scan_names)

    # Get the list names sorted for dictionary
    rnames = (name for name in const_names if 'R' in name)
    anames = (name for name in const_names if 'A' in name)
    dnames = (name for name in const_names if 'D' in name)
    rnames = tuple(sorted(rnames, key=lambda x: int(x.split('R')[1])))
    anames = tuple(sorted(anames, key=lambda x: int(x.split('A')[1])))
    dnames = tuple(sorted(dnames, key=lambda x: int(x.split('D')[1])))
    constraint_names = rnames + anames + dnames

    # Remove the scan coordinates so they are not placed in the dict
    print('rnames', rnames)
    print('anames', anames)
    print('dnames', dnames)
    print('constraint_names', constraint_names)
    constraint_names = tuple(name for name in constraint_names
                             if name not in scan_names)
    print('constraint_names', constraint_names)

    # Build dictionary
    if constraint_names:
        zma_vals = automol.zmatrix.values(zma)
        zma_coords = automol.zmatrix.coordinates(zma)
        assert set(constraint_names) <= set(zma_coords.keys()), (
            'Attempting to constrain coordinates not in zma:\n{}\n{}'.format(
                constraint_names, zma_coords)
        )

        constraint_dct = dict(zip(
            constraint_names,
            (round(zma_vals[name], 2) for name in constraint_names)
        ))
    else:
        constraint_dct = None

    # print('dct')
    # print(constraint_dct)
    # import sys
    # sys.exit()

    return constraint_dct


def set_hr_dims(tors_grids):
    """ Determine the dimensions of the grid
    """
    assert len(tors_grids) in (1, 2, 3, 4), 'Rotor must be 1-4 dimensions'

    grid_points = ((i for i in range(len(grid)))
                   for grid in tors_grids)
    grid_vals = ((x for x in grid)
                 for grid in tors_grids)
    grid_points = itertools.product(*grid_points)
    grid_vals = itertools.product(*grid_vals)

    return grid_points, grid_vals


# Functions to handle setting up groups and axes used to define torstions
def set_tors_def_info(zma, tors_name, tors_sym, pot,
                      ts_bnd, rxn_class, saddle=False):
    """ set stuff
    """
    group, axis, atm_key = _set_groups_ini(
        zma, tors_name, ts_bnd, saddle)
    if saddle:
        group, axis, pot, chkd_sym_num = _check_saddle_groups(
            zma, rxn_class, group, axis,
            pot, ts_bnd, tors_sym)
    else:
        chkd_sym_num = tors_sym
    group = list(numpy.add(group, 1))
    axis = list(numpy.add(axis, 1))
    if (atm_key+1) != axis[1]:
        axis.reverse()

    return group, axis, chkd_sym_num


def _set_groups_ini(zma, tors_name, ts_bnd, saddle):
    """ Set the initial set of groups
    """
    gra = automol.zmatrix.graph(zma, remove_stereo=True)
    coo_dct = automol.zmatrix.coordinates(zma, multi=False)
    axis = coo_dct[tors_name][1:3]
    atm_key = axis[1]
    if ts_bnd:
        for atm in axis:
            if atm in ts_bnd:
                atm_key = atm
                break
    group = list(
        automol.graph.branch_atom_keys(
            gra, atm_key, axis, saddle=saddle, ts_bnd=ts_bnd) - set(axis))
    if not group:
        for atm in axis:
            if atm != atm_key:
                atm_key = atm
        group = list(
            automol.graph.branch_atom_keys(
                gra, atm_key, axis, saddle=saddle, ts_bnd=ts_bnd) - set(axis))

    return group, axis, atm_key


def _check_saddle_groups(zma, rxn_class, group, axis, pot, ts_bnd, sym_num):
    """ Assess that hindered rotor groups and axes
    """
    n_atm = automol.zmatrix.count(zma)
    if 'addition' in rxn_class or 'abstraction' in rxn_class:
        group2 = []
        ts_bnd1 = min(ts_bnd)
        ts_bnd2 = max(ts_bnd)
        for idx in range(ts_bnd2, n_atm):
            group2.append(idx)
        if ts_bnd1 in group:
            for atm in group2:
                if atm not in group:
                    group.append(atm)

    # Check to see if symmetry of XH3 rotor was missed
    if sym_num == 1:
        group2 = []
        for idx in range(n_atm):
            if idx not in group and idx not in axis:
                group2.append(idx)
        all_hyd = True
        symbols = automol.zmatrix.symbols(zma)
        hyd_count = 0
        for idx in group2:
            if symbols[idx] != 'H' and symbols[idx] != 'X':
                all_hyd = False
                break
            if symbols[idx] == 'H':
                hyd_count += 1
        if all_hyd and hyd_count == 3:
            sym_num = 3
            lpot = int(len(pot)/3)
            potp = []
            potp[0:lpot] = pot[0:lpot]
            pot = potp

    return group, axis, pot, sym_num


# CALCULATE THE ZPES OF EACH TORSION USING MESS
def mess_tors_zpes(tors_geo, hind_rot_str, tors_save_path,
                   script_str=DEFAULT_SCRIPT_DCT['messpf']):
    """ Calculate the frequencies and ZPVES of the hindered rotors
        create a messpf input and run messpf to get tors_freqs and tors_zpes
    """

    # Set up the filesys
    bld_locs = ['PF', 0]
    bld_save_fs = autofile.fs.build(tors_save_path)
    bld_save_fs[-1].create(bld_locs)
    pf_path = bld_save_fs[-1].path(bld_locs)
    print('Run path for MESSPF:')
    print(pf_path)

    # Write the MESSPF input file
    global_pf_str = mess_io.writer.global_pf(
        temperatures=[100.0, 200.0, 300.0, 400.0, 500],
        rel_temp_inc=0.001,
        atom_dist_min=0.6)
    dat_str = mess_io.writer.molecule(
        core=mess_io.writer.core_rigidrotor(tors_geo, 1.0),
        freqs=[1000.0],
        elec_levels=[[0.0, 1.0]],
        hind_rot=hind_rot_str,
    )
    spc_str = mess_io.writer.species(
        spc_label='Tmp',
        spc_data=dat_str,
        zero_energy=0.0
    )
    pf_inp_str = '\n'.join([global_pf_str, spc_str]) + '\n'

    with open(os.path.join(pf_path, 'pf.inp'), 'w') as pf_file:
        pf_file.write(pf_inp_str)

    # Run MESSPF
    run_script(script_str, pf_path)

    # Obtain the torsional zpes from the MESS output
    with open(os.path.join(pf_path, 'pf.log'), 'r') as mess_file:
        output_string = mess_file.read()
    tors_zpes = mess_io.reader.tors.zpves(output_string)
    tors_zpe = sum(tors_zpes) if tors_zpes else 0.0

    return tors_zpe
