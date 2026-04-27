# **核心补充文献调研与评估列表**

## **1\. 商业软件核心理论与工业标准 (Industrial Implementation)**

### **1.1 Parallel Execution in Abaqus/Explicit (2024 Guide)**

* **类型**：Commercial Documentation (SIMULIA)  

* **年份**：2024 (v2024 Refresh)  

* **原始链接**：[Abaqus 2024 Online Documentation](https://docs.software.vt.edu/abaqusv2024/English/SIMACAEEXCRefMap/simaexc-c-parallelexecution.htm)  

* **选择理由（针对性补充）**：  
  * **终结“着色”争议**：文档明确指出 Abaqus/Explicit 默认且推荐的并行方式是 **"Domain-level parallelization" (域级并行)**，而非单元级着色。  
  * **实操细节**：详细描述了如何通过 dynamic\_load\_balancing 参数处理计算负载不均，这是学术论文常忽略但工程极其关键的细节。  
  
  

### **1.2 ANSYS Mechanical HPC & Domain Decomposition Method**

* **类型**：Commercial White Paper / Help System  

* **年份**：2021/2022 Update  

* **原始链接**：  
  * [Ansys DDM Theory Guide (Electronics/General)](https://ansyshelp.ansys.com/public//Views/Secured/Electronics/v252/en/Subsystems/HFSS/Content/HFSS/DomainDecompositionMethod.htm)  
  * [Ansys Distributed Architecture Presentation (Classic Ref)](https://teratec.eu/library/pdf/forum/2011/presentations/A6_02_FTeratec_2011_Louat_Ansys.pdf)  
  
* **选择理由（针对性补充）**：  
  * **分布式架构确认**：证实了 Ansys 采用 "Distributed Sparse Solver" 配合 DDM，将求解与组装过程完全分布化，验证了附件中关于“MPI+X”模式在超大规模计算中的统治地位。  
  * **性能数据**：提供了不同核心数（高达1024核）下的加速比数据，作为评估自研算法性能的基准线（Baseline）。  
  
  

## **2\. 混合精度与高性能计算前沿 (Mixed Precision & Frontiers)**

### **2.1 GPU-accelerated Linear Solvers for High-order FEM in Poisson Problems**

* **类型**：Ph.D. Dissertation (Virginia Tech)  

* **作者**：M. Ali (Advisor: C. Warburton)  

* **年份**：**2025 (Latest)**  

* **原始链接**：[Virginia Tech Repository](https://vtechworks.lib.vt.edu/items/8ccfb3ae-7a91-4aa5-8ea9-14fbf0f8be5d)  

* **选择理由（针对性补充）**：  
  * **填补“精度”空白**：这是目前极少数深入探讨 **"Adaptive Mixed Precision" (自适应混合精度)** 在有限元求解器中应用的博士论文。它提出利用 GPU Tensor Cores 的低精度能力加速计算，同时用高精度保证收敛。  
  * **高阶单元优化**：针对高阶单元（High-order FEM）的特殊优化，补充了附件中仅侧重低阶单元组装的不足。  
  
  

### **2.2 GPU-accelerated matrix-free solvers for cardiac electrophysiology**

* **类型**：Ph.D./Master Thesis (Politecnico di Milano)  

* **年份**：2023/2024  

* **原始链接**：[Politecnico di Milano Archive](https://www.politesi.polimi.it/retrieve/c85c5e74-56c3-44e5-832a-dabc55507ff1/Francesco_Carlo_Mantegazza_thesis.pdf)  

* **选择理由（针对性补充）**：  
  * **无矩阵方法实证**：详细展示了 **Matrix-Free (无矩阵)** 方法在复杂多物理场（心脏电生理）中的应用。  
  * **Sum-Factorization**：深入剖析了张量收缩（Sum-Factorization）技术如何降低访存压力，是对附件“无矩阵方法”章节的最佳技术扩充。  
  
  

## **3\. 异构架构与复杂非线性优化 (Heterogeneous & Non-linear)**

### **3.1 Development of GPU-based Strategies for FE Simulation of Elastoplastic Problems**

* **类型**：Ph.D. Synopsis (IIT Guwahati)  

* **作者**：Utpal Kiran  

* **年份**：**2023**  

* **原始链接**：[IIT Guwahati Library](https://fac.iitg.ac.in/dsharma/papers/students/Synopsis_Utpal.pdf)  

* **选择理由（针对性补充）**：  
  * **非线性材料填补**：附件多讨论线性问题（泊松/弹性），此文献专注于 **"Elastoplastic" (弹塑性)** 材料。  
  * **端到端GPU策略**：提出了一种全GPU流程，专门解决非线性迭代中频繁的本构积分和切线刚度矩阵更新问题，对比了Coloring方法在非线性场景下的表现。  
  
  

### **3.2 GPU-accelerated Finite Element Analysis for solid mechanics**

* **类型**：Master Thesis (TU Delft)  

* **作者**：S.M.N. van Paasen  

* **年份**：2023  

* **原始链接**：[TU Delft Repository](https://repository.tudelft.nl/record/uuid:90a5f83c-e388-4d7d-8af4-3f3a9f3e9082)  

* **选择理由（针对性补充）**：  
  * **异构流水线设计**：不同于“全GPU”激进策略，该文探讨了 **CPU-GPU Co-processing**，即利用CPU处理复杂逻辑、GPU处理密集计算的协同模式。  
  * **3000万单元级验证**：在千万级网格规模上进行了验证，数据真实可信。  
  
  