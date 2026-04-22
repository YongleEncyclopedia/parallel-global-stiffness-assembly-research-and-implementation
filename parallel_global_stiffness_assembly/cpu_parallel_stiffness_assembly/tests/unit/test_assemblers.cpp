/**
 * @file test_assemblers.cpp
 * @brief 组装器单元测试
 */

#include <gtest/gtest.h>
#include "core/mesh.h"
#include "assembly/assembler_factory.h"

using namespace fem;

class AssemblerTest : public ::testing::Test {
protected:
    void SetUp() override {
        mesh.generate_cube_mesh(5, 5, 5, 1.0, 1.0, 1.0, ElementType::Hex8);
        csr = mesh.precompute_csr_structure();
    }

    Mesh mesh;
    CsrMatrix csr;
};

TEST_F(AssemblerTest, SerialAssembler) {
    auto assembler = AssemblerFactory::create_serial();
    assembler->set_mesh(mesh);
    assembler->set_csr_structure(csr);

    assembler->prepare();
    assembler->assemble();

    const auto& result = assembler->get_result();
    EXPECT_TRUE(result.is_valid());
    EXPECT_GT(result.frobenius_norm(), 0.0);
}

// GPU 测试需要 CUDA 环境
#ifdef USE_CUDA
TEST_F(AssemblerTest, AtomicAssembler) {
    auto assembler = AssemblerFactory::create_atomic();
    assembler->set_mesh(mesh);
    assembler->set_csr_structure(csr);

    assembler->prepare();
    assembler->assemble();

    const auto& result = assembler->get_result();
    EXPECT_TRUE(result.is_valid());
}
#endif
