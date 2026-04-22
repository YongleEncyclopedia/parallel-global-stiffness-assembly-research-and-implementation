#pragma once

#include "core/types.h"

namespace fem {

class DofMap {
public:
    static Index node_dof(Index node_id, int component) {
        return node_id * constants::DOFS_PER_NODE + component;
    }
};

} // namespace fem
