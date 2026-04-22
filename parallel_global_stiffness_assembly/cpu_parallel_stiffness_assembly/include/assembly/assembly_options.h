#pragma once

#include "core/types.h"

#include <string>

namespace fem {

struct AssemblyOptions {
    int threads = 1;
    KernelType kernel = KernelType::Simplified;
    Real young_modulus = constants::DEFAULT_YOUNG_MODULUS;
    Real poisson_ratio = constants::DEFAULT_POISSON_RATIO;
    Size max_transient_bytes = static_cast<Size>(8ull * 1024ull * 1024ull * 1024ull);
    bool verbose = false;
};

AssemblyOptions make_default_options();

} // namespace fem
