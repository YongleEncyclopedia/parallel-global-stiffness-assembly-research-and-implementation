#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

#ifdef CSC3_DEMO_HAS_EIGEN
#include <Eigen/Core>
#endif

namespace csc3_demo {

using Index = std::int32_t;
using ElementId = std::int32_t;
using NodeId = std::int32_t;

struct DofCodingInfo {
    std::unordered_map<ElementId, std::vector<NodeId>> elems;
    std::unordered_map<NodeId, std::vector<Index>> node_dofs;
};

struct Csc3Matrix {
    Index n = 0;
    std::vector<Index> col_ptr;
    std::vector<Index> row_idx;
    std::vector<double> values;
};

struct HelpInfo {
    std::vector<ElementId> element_ids;
    std::vector<Index> element_dof_offsets;
    std::vector<Index> element_dofs;
    std::vector<Index> entry_offsets;
    std::vector<Index> scatter;
};

class AssemblyHelper {
public:
    void symbolic(const DofCodingInfo& info);
    void zero_values();
    void add(ElementId elem_id, const double* ke_row_major, std::size_t size);
    void add(ElementId elem_id, const std::vector<double>& ke_row_major);
    void add_parallel(const std::unordered_map<ElementId, std::vector<double>>& element_matrices,
                      int threads);

#ifdef CSC3_DEMO_HAS_EIGEN
    void add(ElementId elem_id, const Eigen::Ref<const Eigen::MatrixXd>& ke);
#endif

    [[nodiscard]] const Csc3Matrix& matrix() const;
    [[nodiscard]] const HelpInfo& help_info() const;

private:
    Csc3Matrix matrix_;
    HelpInfo help_info_;
    std::unordered_map<ElementId, std::size_t> element_to_ordinal_;
};

std::vector<double> expand_upper_csc_to_dense(const Csc3Matrix& matrix);
std::string generate_demo_report();
bool openmp_enabled();

} // namespace csc3_demo
