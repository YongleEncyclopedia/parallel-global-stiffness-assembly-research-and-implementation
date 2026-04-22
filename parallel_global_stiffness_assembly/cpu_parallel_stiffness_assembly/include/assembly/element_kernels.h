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
