import argparse
import json
import multiprocessing as mp

import h5py
import numpy as np
from gc_utils import iteration_name, open_snapshot, snapshot_name  # type: ignore

from tools.gc_kinematics import get_kinematics


def main(
    simulation: str,
    it_lst: list[int],
    snap_lst: list[int],
    # snapshot,
    sim_dir: str,
    data_dir: str,
    shared_dict: dict = {},
):
    fire_dir = sim_dir + simulation + "/" + simulation + "_res7100/"

    for snapshot in snap_lst:
        part = open_snapshot(snapshot, fire_dir)
        print(snapshot)
        get_kinematics(part, simulation, it_lst, snapshot, sim_dir, data_dir, shared_dict)

    # part = open_snapshot(snapshot, fire_dir)
    # print(snapshot)
    # get_kinematics(part, simulation, it_lst, snapshot, sim_dir, data_dir, shared_dict)


def add_kinematics_hdf5(simulation, it_lst: list[int], snap_lst: list[int], result_dict: dict, sim_dir: str):
    proc_file = sim_dir + simulation + "/" + simulation + "_processed.hdf5"
    proc_data = h5py.File(proc_file, "a")  # open processed data file

    for it in it_lst:
        it_id = iteration_name(it)
        if it_id in proc_data.keys():
            it_grouping = proc_data[it_id]
        else:
            it_grouping = proc_data.create_group(it_id)
        if "snapshots" in it_grouping.keys():
            snap_groups = it_grouping["snapshots"]
        else:
            snap_groups = it_grouping.create_group("snapshots")
        for snap in snap_lst:
            snap_id = snapshot_name(snap)
            if snap_id in snap_groups.keys():
                snapshot = snap_groups[snap_id]
            else:
                snapshot = snap_groups.create_group(snap_id)
            for key in result_dict[snap_id][it_id].keys():
                snapshot.create_dataset(key, data=result_dict[snap_id][it_id][key])

    proc_data.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--simulation", required=True, type=str, help="simulation name (e.g. m12i)")
    parser.add_argument("-l", "--it_min", required=True, type=int, help="lower bound iteration")
    parser.add_argument("-u", "--it_max", required=True, type=int, help="upper bound iteration")
    parser.add_argument("-c", "--cores", required=False, type=int, help="number of cores to run process on")
    args = parser.parse_args()

    it_min = args.it_min
    it_max = args.it_max
    it_lst = np.linspace(it_min, it_max, it_max - it_min + 1, dtype=int)

    sim = args.simulation

    sim_dir = "/Users/z5114326/Documents/simulations/"
    data_dir = "/Users/z5114326/Documents/GitHub/gc_kinematics_new/data/"

    potential_snaps = data_dir + "external/potentials.json"
    with open(potential_snaps) as json_file:
        pot_data = json.load(json_file)

    snap_lst = np.array(pot_data[sim], dtype=int)
    # snap_lst = snap_lst[:2]

    cores = args.cores
    if cores is None:
        cores = mp.cpu_count()

    snap_groups = np.array_split(snap_lst, cores)
    print(snap_groups)

    with mp.Manager() as manager:
        shared_dict = manager.dict()  # Shared dictionary across processes
        args = [(sim, it_lst, snap_group, sim_dir, data_dir, shared_dict) for snap_group in snap_groups]

        with mp.Pool(processes=cores, maxtasksperchild=1) as pool:
            pool.starmap(main, args, chunksize=1)

        result_dict = dict(shared_dict)

    add_kinematics_hdf5(sim, it_lst, snap_lst, result_dict, sim_dir)
