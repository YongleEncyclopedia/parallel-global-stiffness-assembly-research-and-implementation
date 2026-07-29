// 声明单元刚度矩阵的计算入口。
// 具体实现同时支持线弹性实体模型和旧的简化测试模型。
#pragma once

#include "assembly/assembly_options.h"
#include "core/mesh.h"
#include "core/types.h"

#include <vector>

namespace fem {

void compute_element_matrix(const Mesh& mesh,
                            Size element_id,
                            const AssemblyOptions& options,
                            std::vector<Real>& ke);

} // namespace fem
