// 集中保存一次组装运行需要的线程数、材料参数、刚度模型和内存限制。
// 各后端读取同一份配置，避免在实现中写死实验条件。
#pragma once

#include "core/types.h"

#include <string>

namespace fem {

struct AssemblyOptions {
    int threads = 1;
    StiffnessModel stiffness_model = StiffnessModel::LinearElasticSolid;
    Real young_modulus = constants::DEFAULT_YOUNG_MODULUS;
    Real poisson_ratio = constants::DEFAULT_POISSON_RATIO;
    Size max_transient_bytes = static_cast<Size>(8ull * 1024ull * 1024ull * 1024ull);
    bool verbose = false;
};

AssemblyOptions make_default_options();

} // namespace fem
