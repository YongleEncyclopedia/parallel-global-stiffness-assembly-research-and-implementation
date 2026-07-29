// 把节点编号映射为三维实体单元使用的全局自由度编号。
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
