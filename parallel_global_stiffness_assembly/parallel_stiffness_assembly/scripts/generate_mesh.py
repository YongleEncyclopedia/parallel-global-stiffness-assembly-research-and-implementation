#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_mesh.py - 网格数据生成脚本

生成用于测试的立方体网格数据
"""

import argparse
import os
import sys

def generate_hex8_mesh(nx, ny, nz, lx=1.0, ly=1.0, lz=1.0):
    """生成 Hex8 六面体网格"""
    # 节点
    num_nodes_x = nx + 1
    num_nodes_y = ny + 1
    num_nodes_z = nz + 1
    total_nodes = num_nodes_x * num_nodes_y * num_nodes_z

    dx = lx / nx
    dy = ly / ny
    dz = lz / nz

    nodes = []
    for k in range(num_nodes_z):
        for j in range(num_nodes_y):
            for i in range(num_nodes_x):
                nodes.append((i * dx, j * dy, k * dz))

    # 单元
    def node_index(i, j, k):
        return i + j * num_nodes_x + k * num_nodes_x * num_nodes_y

    elements = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                elem = [
                    node_index(i,     j,     k    ),
                    node_index(i + 1, j,     k    ),
                    node_index(i + 1, j + 1, k    ),
                    node_index(i,     j + 1, k    ),
                    node_index(i,     j,     k + 1),
                    node_index(i + 1, j,     k + 1),
                    node_index(i + 1, j + 1, k + 1),
                    node_index(i,     j + 1, k + 1),
                ]
                elements.append(elem)

    return nodes, elements, "Hex8"


def generate_tet4_mesh(nx, ny, nz, lx=1.0, ly=1.0, lz=1.0):
    """生成 Tet4 四面体网格（通过分解 Hex8）"""
    num_nodes_x = nx + 1
    num_nodes_y = ny + 1
    num_nodes_z = nz + 1

    dx = lx / nx
    dy = ly / ny
    dz = lz / nz

    nodes = []
    for k in range(num_nodes_z):
        for j in range(num_nodes_y):
            for i in range(num_nodes_x):
                nodes.append((i * dx, j * dy, k * dz))

    def node_index(i, j, k):
        return i + j * num_nodes_x + k * num_nodes_x * num_nodes_y

    elements = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                n0 = node_index(i,     j,     k    )
                n1 = node_index(i + 1, j,     k    )
                n2 = node_index(i + 1, j + 1, k    )
                n3 = node_index(i,     j + 1, k    )
                n4 = node_index(i,     j,     k + 1)
                n5 = node_index(i + 1, j,     k + 1)
                n6 = node_index(i + 1, j + 1, k + 1)
                n7 = node_index(i,     j + 1, k + 1)

                # 6 个四面体分解
                elements.append([n0, n1, n3, n4])
                elements.append([n1, n2, n3, n6])
                elements.append([n1, n4, n5, n6])
                elements.append([n3, n4, n6, n7])
                elements.append([n1, n3, n4, n6])
                elements.append([n0, n1, n4, n5])

    return nodes, elements, "Tet4"


def save_mesh(filename, nodes, elements, elem_type):
    """保存网格到文件"""
    with open(filename, 'w') as f:
        f.write(f"{elem_type} {len(nodes)} {len(elements)}\n")

        for x, y, z in nodes:
            f.write(f"{x:.10e} {y:.10e} {z:.10e}\n")

        for elem in elements:
            f.write(" ".join(map(str, elem)) + "\n")

    print(f"Saved: {filename}")
    print(f"  Type: {elem_type}")
    print(f"  Nodes: {len(nodes)}")
    print(f"  Elements: {len(elements)}")
    print(f"  DOFs: {len(nodes) * 3}")


def main():
    parser = argparse.ArgumentParser(description="Generate mesh data for testing")
    parser.add_argument("--type", choices=["hex8", "tet4"], default="hex8",
                        help="Element type (default: hex8)")
    parser.add_argument("--dof", type=int, default=10000,
                        help="Target number of DOFs (default: 10000)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output filename")
    parser.add_argument("--all", action="store_true",
                        help="Generate all standard test meshes")

    args = parser.parse_args()

    # 创建输出目录
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "meshes")
    os.makedirs(output_dir, exist_ok=True)

    if args.all:
        # 生成所有标准测试网格
        test_cases = [
            ("hex8", 10000,   "hex8_10k.mesh"),
            ("hex8", 100000,  "hex8_100k.mesh"),
            ("hex8", 1000000, "hex8_1M.mesh"),
            ("tet4", 10000,   "tet4_10k.mesh"),
            ("tet4", 100000,  "tet4_100k.mesh"),
            ("tet4", 1000000, "tet4_1M.mesh"),
        ]

        for elem_type, target_dof, filename in test_cases:
            # 估算网格尺寸
            if elem_type == "hex8":
                # DOF = (n+1)^3 * 3, n ≈ (DOF/3)^(1/3) - 1
                n = int((target_dof / 3) ** (1/3))
                nodes, elements, etype = generate_hex8_mesh(n, n, n)
            else:
                n = int((target_dof / 3) ** (1/3))
                nodes, elements, etype = generate_tet4_mesh(n, n, n)

            filepath = os.path.join(output_dir, filename)
            save_mesh(filepath, nodes, elements, etype)
            print()
    else:
        # 生成单个网格
        target_dof = args.dof
        n = int((target_dof / 3) ** (1/3))

        if args.type == "hex8":
            nodes, elements, etype = generate_hex8_mesh(n, n, n)
        else:
            nodes, elements, etype = generate_tet4_mesh(n, n, n)

        if args.output:
            filepath = args.output
        else:
            filepath = os.path.join(output_dir, f"{args.type}_{target_dof//1000}k.mesh")

        save_mesh(filepath, nodes, elements, etype)


if __name__ == "__main__":
    main()
