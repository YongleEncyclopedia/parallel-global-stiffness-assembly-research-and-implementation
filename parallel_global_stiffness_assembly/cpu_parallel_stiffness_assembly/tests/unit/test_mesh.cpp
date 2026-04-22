/**
 * @file test_mesh.cpp
 * @brief Mesh 类单元测试
 */

#include <gtest/gtest.h>
#include "core/mesh.h"

using namespace fem;

TEST(MeshTest, GenerateHex8Mesh) {
    Mesh mesh;
    mesh.generate_cube_mesh(5, 5, 5, 1.0, 1.0, 1.0, ElementType::Hex8);

    EXPECT_EQ(mesh.num_nodes(), 6 * 6 * 6);
    EXPECT_EQ(mesh.num_elements(), 5 * 5 * 5);
    EXPECT_EQ(mesh.num_dofs(), 6 * 6 * 6 * 3);
    EXPECT_EQ(mesh.nodes_per_element(), 8);
}

TEST(MeshTest, GenerateTet4Mesh) {
    Mesh mesh;
    mesh.generate_cube_mesh(5, 5, 5, 1.0, 1.0, 1.0, ElementType::Tet4);

    EXPECT_EQ(mesh.num_nodes(), 6 * 6 * 6);
    EXPECT_EQ(mesh.num_elements(), 5 * 5 * 5 * 6);  // 每个 Hex8 分解为 6 个 Tet4
    EXPECT_EQ(mesh.nodes_per_element(), 4);
}

TEST(MeshTest, PrecomputeCsrStructure) {
    Mesh mesh;
    mesh.generate_cube_mesh(3, 3, 3, 1.0, 1.0, 1.0, ElementType::Hex8);

    CsrMatrix csr = mesh.precompute_csr_structure();

    EXPECT_EQ(csr.num_rows, mesh.num_dofs());
    EXPECT_EQ(csr.num_cols, mesh.num_dofs());
    EXPECT_TRUE(csr.is_valid());
    EXPECT_GT(csr.nnz, 0);
}
