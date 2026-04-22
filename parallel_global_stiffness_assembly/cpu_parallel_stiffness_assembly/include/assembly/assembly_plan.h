#pragma once

#include "core/csr_matrix.h"
#include "core/mesh.h"
#include "core/types.h"

#include <vector>

namespace fem {

struct AssemblyPlan {
    std::vector<Index> element_offsets;
    std::vector<Index> dofs;
    std::vector<Index> scatter;

    [[nodiscard]] Size num_elements() const noexcept {
        return element_offsets.empty() ? 0 : element_offsets.size() - 1;
    }

    [[nodiscard]] int element_dof_count(Size elem) const {
        return static_cast<int>(element_offsets[elem + 1] - element_offsets[elem]);
    }

    [[nodiscard]] const Index* element_dofs_ptr(Size elem) const {
        return dofs.data() + element_offsets[elem];
    }

    [[nodiscard]] const Index* element_scatter_ptr(Size elem) const {
        const auto off = element_offsets[elem];
        const auto n = element_offsets[elem + 1] - off;
        return scatter.data() + off * static_cast<Index>(n);
    }

    [[nodiscard]] Size bytes() const noexcept {
        return (element_offsets.size() + dofs.size() + scatter.size()) * sizeof(Index);
    }
};

AssemblyPlan build_assembly_plan(const Mesh& mesh, const CsrMatrix& csr);

} // namespace fem
