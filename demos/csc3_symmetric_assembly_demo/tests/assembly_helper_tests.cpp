#include "csc3_demo/assembly_helper.h"

#include <algorithm>
#include <cmath>
#include <exception>
#include <iostream>
#include <limits>
#include <random>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace {

using namespace csc3_demo;

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

template <typename T>
void require_equal(const std::vector<T>& actual,
                   const std::vector<T>& expected,
                   const std::string& label) {
    if (actual != expected) {
        throw std::runtime_error(label + " mismatch");
    }
}

void require_close(const std::vector<double>& actual,
                   const std::vector<double>& expected,
                   const std::string& label,
                   double tol = 1.0e-12) {
    require_true(actual.size() == expected.size(), label + " size mismatch");
    for (std::size_t i = 0; i < actual.size(); ++i) {
        if (!std::isfinite(actual[i]) || std::abs(actual[i] - expected[i]) > tol) {
            throw std::runtime_error(label + " value mismatch at index " + std::to_string(i));
        }
    }
}

template <typename Fn>
void require_throws(Fn fn, const std::string& label) {
    try {
        fn();
    } catch (const std::exception&) {
        return;
    }
    throw std::runtime_error(label + " did not throw");
}

Index csc_position(const Csc3Matrix& matrix, Index row, Index col) {
    const Index begin = matrix.col_ptr[static_cast<std::size_t>(col)];
    const Index end = matrix.col_ptr[static_cast<std::size_t>(col) + 1];
    const auto first = matrix.row_idx.begin() + begin;
    const auto last = matrix.row_idx.begin() + end;
    const auto it = std::lower_bound(first, last, row);
    if (it == last || *it != row) {
        throw std::runtime_error("expected CSC3 entry is missing");
    }
    return static_cast<Index>(std::distance(matrix.row_idx.begin(), it));
}

DofCodingInfo chain_info() {
    return DofCodingInfo{
        {{10, {0, 1}}, {20, {1, 2}}},
        {{0, {0}}, {1, {1}}, {2, {2}}}
    };
}

void test_chain_1d_upper_csc3() {
    AssemblyHelper helper;
    helper.symbolic(chain_info());

    const auto& matrix = helper.matrix();
    require_true(matrix.n == 3, "chain matrix dimension");
    require_equal(matrix.col_ptr, std::vector<Index>{0, 1, 3, 5}, "chain col_ptr");
    require_equal(matrix.row_idx, std::vector<Index>{0, 0, 1, 1, 2}, "chain row_idx");

    helper.add(10, std::vector<double>{2.0, -1.0, -1.0, 2.0});
    helper.add(20, std::vector<double>{3.0, -2.0, -2.0, 3.0});
    require_close(matrix.values, std::vector<double>{2.0, -1.0, 5.0, -2.0, 3.0}, "chain values");
}

void test_triangle_2d_variable_dofs() {
    DofCodingInfo info{
        {{7, {3, 1, 2}}},
        {{1, {2, 3}}, {2, {4, 5}}, {3, {0, 1}}}
    };
    AssemblyHelper helper;
    helper.symbolic(info);

    const auto& matrix = helper.matrix();
    require_true(matrix.n == 6, "triangle matrix dimension");
    require_true(matrix.values.size() == 21, "triangle upper nnz");

    std::vector<double> ke(36, 0.0);
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            ke[static_cast<std::size_t>(r * 6 + c)] =
                (r == c) ? static_cast<double>(10 + r) : static_cast<double>(r + c + 1);
        }
    }
    helper.add(7, ke);

    std::vector<double> expected_dense(36, 0.0);
    const std::vector<Index> dofs{0, 1, 2, 3, 4, 5};
    for (int i = 0; i < 6; ++i) {
        for (int j = 0; j < 6; ++j) {
            expected_dense[static_cast<std::size_t>(dofs[i] * 6 + dofs[j])] =
                ke[static_cast<std::size_t>(i * 6 + j)];
        }
    }
    require_close(expand_upper_csc_to_dense(matrix), expected_dense, "triangle dense");
}

void test_shared_elements_parallel_atomic() {
    AssemblyHelper serial;
    serial.symbolic(chain_info());
    serial.add(10, std::vector<double>{2.0, -1.0, -1.0, 2.0});
    serial.add(20, std::vector<double>{3.0, -2.0, -2.0, 3.0});

    AssemblyHelper parallel;
    parallel.symbolic(chain_info());
    parallel.add_parallel({
        {20, {3.0, -2.0, -2.0, 3.0}},
        {10, {2.0, -1.0, -1.0, 2.0}}
    }, 4);

    require_equal(parallel.matrix().col_ptr, serial.matrix().col_ptr, "parallel col_ptr");
    require_equal(parallel.matrix().row_idx, serial.matrix().row_idx, "parallel row_idx");
    require_close(parallel.matrix().values, serial.matrix().values, "parallel values");
}

void test_global_duplicate_dof_rejected() {
    require_throws([] {
        AssemblyHelper helper;
        helper.symbolic(DofCodingInfo{
            {{10, {0}}, {20, {1}}},
            {{0, {0}}, {1, {0}}}
        });
    }, "global duplicate dof");
}

void test_local_dof_order_uses_local_upper_entry() {
    AssemblyHelper helper;
    helper.symbolic(DofCodingInfo{
        {{1, {1, 0}}},
        {{0, {0}}, {1, {1}}}
    });

    helper.add(1, std::vector<double>{
        10.0, 7.00000000005,
        7.0, 20.0
    });

    require_close(helper.matrix().values,
                  std::vector<double>{20.0, 7.00000000005, 10.0},
                  "local upper value for unordered dofs");
}

void test_non_finite_local_matrix_rejected() {
    require_throws([] {
        AssemblyHelper helper;
        helper.symbolic(chain_info());
        const double nan = std::numeric_limits<double>::quiet_NaN();
        helper.add(10, std::vector<double>{1.0, nan, nan, 1.0});
    }, "nan local matrix");

    require_throws([] {
        AssemblyHelper helper;
        helper.symbolic(chain_info());
        const double inf = std::numeric_limits<double>::infinity();
        helper.add(10, std::vector<double>{1.0, inf, inf, 1.0});
    }, "inf local matrix");
}

void test_add_parallel_requires_all_elements() {
    require_throws([] {
        AssemblyHelper helper;
        helper.symbolic(chain_info());
        helper.add_parallel({{10, {2.0, -1.0, -1.0, 2.0}}}, 4);
    }, "missing element matrix");
}

void test_add_parallel_rejects_unknown_element() {
    require_throws([] {
        AssemblyHelper helper;
        helper.symbolic(chain_info());
        helper.add_parallel({
            {10, {2.0, -1.0, -1.0, 2.0}},
            {20, {3.0, -2.0, -2.0, 3.0}},
            {30, {1.0}}
        }, 4);
    }, "unknown element matrix");
}

void test_scatter_invariant() {
    DofCodingInfo info{
        {{5, {2, 0}}, {9, {1, 2}}},
        {{0, {2, 0}}, {1, {3}}, {2, {1}}}
    };
    AssemblyHelper helper;
    helper.symbolic(info);

    const auto& matrix = helper.matrix();
    const auto& help = helper.help_info();
    require_true(help.scatter.size() == static_cast<std::size_t>(help.entry_offsets.back()),
                 "scatter size must match entry_offsets.back()");
    for (Index p : help.scatter) {
        require_true(p >= 0 && static_cast<std::size_t>(p) < matrix.values.size(),
                     "scatter index out of range");
    }
    for (std::size_t ordinal = 0; ordinal < help.element_ids.size(); ++ordinal) {
        const std::size_t begin = static_cast<std::size_t>(help.element_dof_offsets[ordinal]);
        const std::size_t end = static_cast<std::size_t>(help.element_dof_offsets[ordinal + 1]);
        std::size_t scatter_pos = static_cast<std::size_t>(help.entry_offsets[ordinal]);
        for (std::size_t i = begin; i < end; ++i) {
            for (std::size_t j = i; j < end; ++j) {
                const Index row = std::min(help.element_dofs[i], help.element_dofs[j]);
                const Index col = std::max(help.element_dofs[i], help.element_dofs[j]);
                require_true(help.scatter[scatter_pos++] == csc_position(matrix, row, col),
                             "scatter points to wrong CSC3 entry");
            }
        }
    }
}

void test_unordered_variable_dofs_dense_oracle() {
    DofCodingInfo info{
        {{7, {1, 0}}},
        {{0, {2, 0}}, {1, {3, 1}}}
    };
    AssemblyHelper helper;
    helper.symbolic(info);

    const std::vector<Index> dofs{3, 1, 2, 0};
    std::vector<double> ke{
        11.0,  1.5,  2.5,  3.5,
         1.5, 12.0,  4.5,  5.5,
         2.5,  4.5, 13.0,  6.5,
         3.5,  5.5,  6.5, 14.0
    };
    helper.add(7, ke);

    std::vector<double> expected(16, 0.0);
    for (std::size_t i = 0; i < dofs.size(); ++i) {
        for (std::size_t j = i; j < dofs.size(); ++j) {
            expected[static_cast<std::size_t>(dofs[i]) * 4 + dofs[j]] += ke[i * 4 + j];
            if (i != j) {
                expected[static_cast<std::size_t>(dofs[j]) * 4 + dofs[i]] += ke[i * 4 + j];
            }
        }
    }
    require_close(expand_upper_csc_to_dense(helper.matrix()), expected, "unordered dense oracle");
}

void test_high_contention_parallel_atomic() {
    DofCodingInfo info;
    info.node_dofs = {{0, {0}}, {1, {1}}};
    std::unordered_map<ElementId, std::vector<double>> matrices;
    for (ElementId e = 0; e < 1000; ++e) {
        info.elems[e] = {0, 1};
        matrices[e] = {1.0, 0.25, 0.25, 2.0};
    }

    AssemblyHelper serial;
    serial.symbolic(info);
    for (ElementId e = 0; e < 1000; ++e) {
        serial.add(e, matrices[e]);
    }

    AssemblyHelper parallel;
    parallel.symbolic(info);
    parallel.add_parallel(matrices, 8);

    require_close(parallel.matrix().values, serial.matrix().values, "high contention values");
}

void test_random_deterministic_oracle() {
    std::mt19937 rng(12345);
    for (int trial = 0; trial < 50; ++trial) {
        const int ndofs = 4 + (trial % 5);
        DofCodingInfo info;
        for (Index node = 0; node < ndofs; ++node) {
            info.node_dofs[node] = {node};
        }

        std::unordered_map<ElementId, std::vector<double>> matrices;
        std::vector<double> expected(static_cast<std::size_t>(ndofs * ndofs), 0.0);
        const int nelems = 3 + (trial % 4);
        for (ElementId elem = 0; elem < nelems; ++elem) {
            std::vector<Index> nodes(ndofs);
            for (Index i = 0; i < ndofs; ++i) nodes[static_cast<std::size_t>(i)] = i;
            std::shuffle(nodes.begin(), nodes.end(), rng);
            const int edofs = 2 + static_cast<int>(rng() % static_cast<unsigned>(ndofs - 1));
            nodes.resize(static_cast<std::size_t>(edofs));
            info.elems[elem] = std::vector<NodeId>(nodes.begin(), nodes.end());

            std::vector<double> ke(static_cast<std::size_t>(edofs * edofs), 0.0);
            for (int i = 0; i < edofs; ++i) {
                for (int j = i; j < edofs; ++j) {
                    const double value = (i == j)
                        ? static_cast<double>(20 + trial + elem + i)
                        : static_cast<double>((trial + 1) * (elem + 1) + i + j) / 10.0;
                    ke[static_cast<std::size_t>(i * edofs + j)] = value;
                    ke[static_cast<std::size_t>(j * edofs + i)] = value;
                    const Index gi = nodes[static_cast<std::size_t>(i)];
                    const Index gj = nodes[static_cast<std::size_t>(j)];
                    expected[static_cast<std::size_t>(gi) * ndofs + gj] += value;
                    if (i != j) {
                        expected[static_cast<std::size_t>(gj) * ndofs + gi] += value;
                    }
                }
            }
            matrices[elem] = ke;
        }

        AssemblyHelper helper;
        helper.symbolic(info);
        helper.add_parallel(matrices, 4);
        require_close(expand_upper_csc_to_dense(helper.matrix()),
                      expected,
                      "random deterministic oracle");
    }
}

#ifdef CSC3_DEMO_HAS_EIGEN
void test_eigen_adapter_validation_failures() {
    require_throws([] {
        AssemblyHelper helper;
        helper.symbolic(chain_info());
        Eigen::MatrixXd ke(2, 3);
        ke.setOnes();
        helper.add(10, ke);
    }, "Eigen non-square local matrix");

    require_throws([] {
        AssemblyHelper helper;
        helper.symbolic(chain_info());
        Eigen::MatrixXd ke = Eigen::MatrixXd::Identity(3, 3);
        helper.add(10, ke);
    }, "Eigen local matrix dimension mismatch");
}
#endif

void test_validation_failures() {
    require_throws([] {
        AssemblyHelper helper;
        helper.symbolic(DofCodingInfo{{{1, {9}}}, {{0, {0}}}});
    }, "missing node");

    require_throws([] {
        AssemblyHelper helper;
        helper.symbolic(DofCodingInfo{{{1, {0, 1}}}, {{0, {0}}, {1, {2}}}});
    }, "non-contiguous dofs");

    require_throws([] {
        AssemblyHelper helper;
        helper.symbolic(DofCodingInfo{{{1, {0, 0}}}, {{0, {0}}, {1, {1}}}});
    }, "duplicate element dof");

    require_throws([] {
        AssemblyHelper helper;
        helper.symbolic(chain_info());
        helper.add(10, std::vector<double>{1.0, 2.0, 3.0});
    }, "bad local matrix size");

    require_throws([] {
        AssemblyHelper helper;
        helper.symbolic(chain_info());
        helper.add(10, std::vector<double>{1.0, 2.0, 3.0, 4.0});
    }, "non-symmetric local matrix");
}

} // namespace

int main() {
    try {
        test_chain_1d_upper_csc3();
        test_triangle_2d_variable_dofs();
        test_shared_elements_parallel_atomic();
        test_global_duplicate_dof_rejected();
        test_local_dof_order_uses_local_upper_entry();
        test_non_finite_local_matrix_rejected();
        test_add_parallel_requires_all_elements();
        test_add_parallel_rejects_unknown_element();
        test_scatter_invariant();
        test_unordered_variable_dofs_dense_oracle();
        test_high_contention_parallel_atomic();
        test_random_deterministic_oracle();
#ifdef CSC3_DEMO_HAS_EIGEN
        test_eigen_adapter_validation_failures();
#endif
        test_validation_failures();
    } catch (const std::exception& ex) {
        std::cerr << ex.what() << '\n';
        return 1;
    }
    return 0;
}
