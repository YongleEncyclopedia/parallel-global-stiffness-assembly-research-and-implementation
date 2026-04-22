#include "assembly/assembly_plan.h"

#include <limits>
#include <stdexcept>

namespace fem {

AssemblyPlan build_assembly_plan(const Mesh& mesh, const CsrMatrix& csr) {
    AssemblyPlan plan;
    plan.element_offsets.reserve(mesh.elements.size() + 1);
    plan.element_offsets.push_back(0);

    Size total_dofs = 0;
    Size total_scatter = 0;
    for (const auto& elem : mesh.elements) {
        const int edofs = elem.node_count * constants::DOFS_PER_NODE;
        total_dofs += static_cast<Size>(edofs);
        total_scatter += static_cast<Size>(edofs) * static_cast<Size>(edofs);
    }
    if (total_dofs > static_cast<Size>(std::numeric_limits<Index>::max()) ||
        total_scatter > static_cast<Size>(std::numeric_limits<Index>::max())) {
        throw std::runtime_error("Assembly plan exceeds 32-bit Index capacity");
    }

    plan.dofs.reserve(total_dofs);
    plan.scatter.reserve(total_scatter);

    for (const auto& elem : mesh.elements) {
        const auto dofs = element_dofs(elem);
        plan.dofs.insert(plan.dofs.end(), dofs.begin(), dofs.end());
        plan.element_offsets.push_back(static_cast<Index>(plan.dofs.size()));
        for (Index r : dofs) {
            for (Index c : dofs) {
                plan.scatter.push_back(csr.find_position(r, c));
            }
        }
    }
    return plan;
}

} // namespace fem
