#include "assembly/assembly_plan.h"

#include "core/platform.h"

#include <algorithm>
#include <cstdint>
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

AssemblyPlan build_assembly_plan_parallel(const Mesh& mesh, const CsrMatrix& csr, int threads) {
    AssemblyPlan plan;
    plan.element_offsets.resize(mesh.elements.size() + 1, 0);

    Size total_dofs = 0;
    Size total_scatter = 0;
    for (Size e = 0; e < mesh.elements.size(); ++e) {
        const int edofs = mesh.elements[e].node_count * constants::DOFS_PER_NODE;
        total_dofs += static_cast<Size>(edofs);
        total_scatter += static_cast<Size>(edofs) * static_cast<Size>(edofs);
        if (total_dofs > static_cast<Size>(std::numeric_limits<Index>::max()) ||
            total_scatter > static_cast<Size>(std::numeric_limits<Index>::max())) {
            throw std::runtime_error("Assembly plan exceeds 32-bit Index capacity");
        }
        plan.element_offsets[e + 1] = static_cast<Index>(total_dofs);
    }

    plan.dofs.resize(total_dofs);
    plan.scatter.resize(total_scatter);
    const int nth = std::max(1, effective_thread_count(threads));

#ifdef _OPENMP
#pragma omp parallel for schedule(static) num_threads(nth)
#endif
    for (std::int64_t ee = 0; ee < static_cast<std::int64_t>(mesh.elements.size()); ++ee) {
        const Size e = static_cast<Size>(ee);
        const auto dofs = element_dofs(mesh.elements[e]);
        const Size dof_offset = static_cast<Size>(plan.element_offsets[e]);
        const int edofs = static_cast<int>(dofs.size());
        std::copy(dofs.begin(), dofs.end(), plan.dofs.begin() + dof_offset);
        Size scatter_offset = dof_offset * static_cast<Size>(edofs);
        for (int i = 0; i < edofs; ++i) {
            for (int j = 0; j < edofs; ++j) {
                plan.scatter[scatter_offset++] = csr.find_position(dofs[static_cast<Size>(i)],
                                                                   dofs[static_cast<Size>(j)]);
            }
        }
    }

    return plan;
}

} // namespace fem
