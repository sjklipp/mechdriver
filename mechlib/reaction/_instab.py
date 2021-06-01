"""
 Library to deal unstable species
"""

import automol
from mechlib import filesys
from mechlib.amech_io import printer as ioprinter


# Handle reaction lst
def split_unstable_rxn(rxn_lst, spc_dct, spc_model_dct_i, save_prefix):
    """ Loop over the reaction list and break up the unstable species
    """

    # Get theory
    thy_info = spc_model_dct_i['vib']['geolvl'][1][1]

    # Loop over the reactions and split
    new_rxn_lst = ()
    for rxn in rxn_lst:

        # Unpack the reaction
        chnl_idx, (rcts, prds) = rxn

        # Build the mapping dictionary for the rxn species
        rxn_names = rcts + prds
        split_map = _split_mapping(spc_dct, thy_info, save_prefix,
                                   spc_names=rxn_names, zma_locs=(0,))

        # Assess and split the reactants and products for unstable species
        new_rcts = ()
        for rct in rcts:
            new_rcts += split_map[rct]

        new_prds = ()
        for prd in prds:
            new_prds += split_map[prd]

        # Check if the split species are in the spc dct
        if len(rcts) > len(new_rcts):
            print('WARNING: REACTANTS FROM SPLIT MISSING FROM SPC DCT')
        if len(prds) > len(new_prds):
            print('WARNING: PRODUCTS FROM SPLIT MISSING FROM SPC DCT')

        # Flip the reaction if the reactants are unstable?

        # Append to list
        new_rxn = ((chnl_idx, (new_rcts, new_prds)),)
        new_rxn_lst += new_rxn

    return new_rxn_lst


def split_unstable_spc(spc_rlst, spc_dct, spc_model_dct_i, save_prefix):
    """ Loop over the reaction list and break up the unstable species
    """

    # Get theory
    thy_info = spc_model_dct_i['vib']['geolvl'][1][1]

    # Loop over the species lst and split as they god
    split_spc_names = ()
    for spc in list(spc_rlst.values())[0]:
        split_spc_names += _split_species(
            spc_dct, spc, thy_info, save_prefix, zma_locs=(0,))

    return {('SPC', 0, 0): split_spc_names}


def _split_mapping(spc_dct, thy_info, save_prefix,
                   spc_names=None, zma_locs=(0,)):
    """ Build a dictionry which maps the names of species into splits
        would like to build to just go over spc dct (good for mech pre-process)
        could do
    """

    if spc_names is None:
        spc_names = tuple(name for name in spc_dct.keys() if 'ts_' not in name)

    split_map = {}
    for spc_name in spc_names:
        split_names = _split_species(
            spc_dct, spc_name, thy_info, save_prefix, zma_locs=zma_locs)
        if split_names:
            split_map[spc_name] = split_names
        else:
            split_map[spc_name] = (spc_name,)

    return split_map


def _split_species(spc_dct, spc_name, thy_info, save_prefix,
                   zma_locs=(0,)):
    """  split up the unstable species
    """

    # Initialize an empty list
    split_names = ()

    # Attempt to read the graph of the instability trans
    # Get the product graphs and inchis
    tra, path = filesys.read.instability_transformation(
        spc_dct, spc_name, thy_info, save_prefix, zma_locs=zma_locs)

    if tra is not None:
        ioprinter.info_message('\nFound instability files at path:')
        ioprinter.info_message('  {}'.format(path))

        zrxn, _ = tra
        prd_gras = automol.reac.product_graphs(zrxn)
        constituent_ichs = tuple(automol.graph.inchi(gra, stereo=True)
                                 for gra in prd_gras)

        for ich in constituent_ichs:
            for name, spc_dct_i in spc_dct.items():
                if ich == spc_dct_i.get('inchi'):
                    split_names += (name,)
                    break
        split_names = tuple(set(split_names))

        print('- Splitting species...')
        print('- New species: {}'.format(' '.join(split_names)))

    return split_names