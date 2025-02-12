'''
-----------------------------------------------------------------------------
Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.

NVIDIA CORPORATION and its licensors retain all intellectual property
and proprietary rights in and to this software, related documentation
and any modifications thereto. Any use, reproduction, disclosure or
distribution of this software and related documentation without an express
license agreement from NVIDIA CORPORATION is strictly prohibited.
-----------------------------------------------------------------------------
'''

import numpy as np
import trimesh
import mcubes
import torch
import torch.distributed as dist
from tqdm import tqdm

from imaginaire.utils.distributed import get_world_size, is_master


@torch.no_grad()
def extract_mesh(sdf_func, bounds, intv, block_res=64):
    lattice_grid = LatticeGrid(bounds, intv=intv, block_res=block_res)
    data_loader = get_lattice_grid_loader(lattice_grid)
    mesh_blocks = []
    if is_master():
        data_loader = tqdm(data_loader, leave=False)
    for it, data in enumerate(data_loader):
        xyz = data["xyz"][0]
        xyz_cuda = xyz.cuda()
        sdf_cuda = sdf_func(xyz_cuda)[..., 0]
        sdf = sdf_cuda.cpu()
        mesh = marching_cubes(sdf.numpy(), xyz.numpy(), intv)
        mesh_blocks.append(mesh)
    mesh_blocks_gather = [None] * get_world_size()
    dist.all_gather_object(mesh_blocks_gather, mesh_blocks)
    if is_master():
        mesh_blocks_all = [mesh for mesh_blocks in mesh_blocks_gather for mesh in mesh_blocks]
        mesh = trimesh.util.concatenate(mesh_blocks_all)
        return mesh
    else:
        return None


class LatticeGrid(torch.utils.data.Dataset):

    def __init__(self, bounds, intv, block_res=64):
        super().__init__()
        self.block_res = block_res
        ((x_min, x_max), (y_min, y_max), (z_min, z_max)) = bounds
        self.x_grid = torch.arange(x_min, x_max, intv)
        self.y_grid = torch.arange(y_min, y_max, intv)
        self.z_grid = torch.arange(z_min, z_max, intv)
        res_x, res_y, res_z = len(self.x_grid), len(self.y_grid), len(self.z_grid)
        print("Extracting surface at resolution", res_x, res_y, res_z)
        self.num_blocks_x = int(np.ceil(res_x / block_res))
        self.num_blocks_y = int(np.ceil(res_y / block_res))
        self.num_blocks_z = int(np.ceil(res_z / block_res))

    def __getitem__(self, idx):
        # Keep track of sample index for convenience.
        sample = dict(idx=idx)
        block_idx_x = idx // (self.num_blocks_y * self.num_blocks_z)
        block_idx_y = (idx // self.num_blocks_z) % self.num_blocks_y
        block_idx_z = idx % self.num_blocks_z
        xi = block_idx_x * self.block_res
        yi = block_idx_y * self.block_res
        zi = block_idx_z * self.block_res
        x, y, z = torch.meshgrid(self.x_grid[xi:xi+self.block_res+1],
                                 self.y_grid[yi:yi+self.block_res+1],
                                 self.z_grid[zi:zi+self.block_res+1], indexing="ij")
        xyz = torch.stack([x, y, z], dim=-1)
        sample.update(xyz=xyz)
        return sample

    def __len__(self):
        return self.num_blocks_x * self.num_blocks_y * self.num_blocks_z


def get_lattice_grid_loader(dataset, num_workers=8):
    if dist.is_initialized():
        sampler = torch.utils.data.distributed.DistributedSampler(dataset, shuffle=False)
    else:
        sampler = None
    return torch.utils.data.DataLoader(
        dataset,
        batch_size=1,
        shuffle=False,
        sampler=sampler,
        pin_memory=True,
        num_workers=num_workers,
        drop_last=False
    )


def marching_cubes(sdf, xyz, intv):
    # marching cubes
    V, F = mcubes.marching_cubes(sdf, 0.)
    V = V * intv + xyz[0, 0, 0]
    mesh = trimesh.Trimesh(V, F)
    mesh = filter_points_outside_bounding_sphere(mesh)
    return mesh


def filter_points_outside_bounding_sphere(old_mesh):
    mask = np.linalg.norm(old_mesh.vertices, axis=-1) < 1.0
    indices = np.ones(len(old_mesh.vertices), dtype=int) * -1
    indices[mask] = np.arange(mask.sum())
    faces_mask = mask[old_mesh.faces[:, 0]] & mask[old_mesh.faces[:, 1]] & mask[old_mesh.faces[:, 2]]
    new_faces = indices[old_mesh.faces[faces_mask]]
    new_vertices = old_mesh.vertices[mask]
    new_mesh = trimesh.Trimesh(new_vertices, new_faces)
    return new_mesh
