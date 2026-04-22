#pragma once

#include "assembly/assembly_options.h"
#include "assembly/assembly_plan.h"
#include "core/csr_matrix.h"
#include "core/mesh.h"
#include "core/types.h"

#include <memory>
#include <string>
#include <vector>

namespace fem {

struct AssemblyStats {
    double preprocess_time_ms = 0.0;
    double assembly_time_ms = 0.0;
    double total_time_ms = 0.0;
    Size memory_usage_bytes = 0;
    Size extra_memory_bytes = 0;
    Size num_elements_processed = 0;
    Size num_dofs = 0;
    Size nnz = 0;
    int colors = 0;
    std::vector<Size> color_sizes;
    std::string diagnostics;
};

class IAssembler {
public:
    virtual ~IAssembler() = default;

    virtual void set_problem(const Mesh& mesh,
                             const CsrMatrix& csr_structure,
                             const AssemblyPlan& plan) = 0;
    virtual void prepare() = 0;
    virtual void assemble() = 0;
    virtual void cleanup() = 0;

    [[nodiscard]] virtual const CsrMatrix& get_result() const = 0;
    [[nodiscard]] virtual CsrMatrix& get_result_mut() = 0;
    [[nodiscard]] virtual AssemblyStats get_stats() const = 0;
    [[nodiscard]] virtual std::string get_name() const = 0;
    [[nodiscard]] virtual AlgorithmType get_type() const = 0;
    [[nodiscard]] virtual bool uses_gpu() const = 0;
};

using AssemblerPtr = std::unique_ptr<IAssembler>;

} // namespace fem
