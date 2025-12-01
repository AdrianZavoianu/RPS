Structural Analysis
===================

.
└── 1. Structural Analysis (Research-Level Computational Mechanics)
    ├── 1.1 Mathematical & Mechanical Foundations
    │   ├── 1.1.1 Continuum Mechanics
    │   │   ├── Stress tensors (Cauchy, PK1, PK2)
    │   │   ├── Strain measures (Green–Lagrange, Almansi, log-strain)
    │   │   ├── Stress/strain invariants and principal values
    │   │   ├── Stress/strain transformation (Mohr’s circle)
    │   │   ├── Deformation gradient F and polar decomposition
    │   │   ├── Objectivity & frame indifference
    │   │   └── Energy conjugacy & stress power
    │   │
    │   ├── 1.1.2 Kinematics of Deformation
    │   │   ├── Linear strain–displacement relations
    │   │   ├── Plane stress & plane strain formulations
    │   │   ├── Finite strain kinematics
    │   │   ├── Corotational, total Lagrangian (TL), updated Lagrangian (UL)
    │   │   └── Compatibility & integrability
    │   │
    │   ├── 1.1.3 Balance Laws
    │   │   ├── Conservation of mass
    │   │   ├── Linear & angular momentum
    │   │   ├── Energy balance & thermodynamics
    │   │   └── Traction boundary conditions
    │   │
    │   └── 1.1.4 Variational Principles
    │       ├── Principle of virtual work (PVW)
    │       ├── Minimum potential energy
    │       ├── Hamilton’s principle
    │       ├── Weighted residuals
    │       └── Galerkin method
    │
    ├── 1.2 Constitutive Modeling (General Material-Agnostic)
    │   ├── 1.2.1 Elasticity
    │   │   ├── Isotropic elasticity
    │   │   ├── Orthotropic & anisotropic elasticity
    │   │   ├── Thermoelasticity (coupled & generalized)
    │   │   ├── Plane stress / plane strain elasticity
    │   │   ├── Analytical elasticity solutions (beams, plates, shells)
    │   │   ├── Elastic half-space solutions
    │   │   └── Elastic contact (Hertzian, axisymmetric, line contact)
    │   │
    │   ├── 1.2.2 Plasticity
    │   │   ├── Yield criteria (von Mises, Tresca, Drucker–Prager)
    │   │   ├── Flow rules (associated / non-associated)
    │   │   ├── Hardening: isotropic, kinematic, mixed (Bauschinger)
    │   │   ├── Finite-strain plasticity
    │   │   ├── Objective stress rates (Jaumann, Green–Naghdi)
    │   │   └── Return-mapping and consistent tangent
    │   │
    │   ├── 1.2.3 Damage & Softening
    │   │   ├── Continuum damage models (Mazars, Lemaitre)
    │   │   ├── Coupled plastic–damage models
    │   │   ├── Strain-softening and localization
    │   │   └── Regularization (integral, gradient)
    │   │
    │   ├── 1.2.4 Fracture Mechanics
    │   │   ├── LEFM (K, G, J-integral)
    │   │   ├── EPFM
    │   │   ├── Mixed-mode (I/II/III)
    │   │   ├── Cohesive zone models
    │   │   └── CTOD, R-curves
    │   │
    │   └── 1.2.5 Fatigue Mechanics
    │       ├── S–N curves & fatigue life
    │       ├── High-cycle / low-cycle fatigue
    │       ├── Paris law crack growth
    │       ├── Crack closure effects
    │       ├── Damage accumulation (Miner’s rule)
    │       └── Variable-amplitude loading & rainflow counting
    │
    ├── 1.3 Structural Stability (General Theory)
    │   ├── 1.3.1 Classical Stability
    │   │   ├── Euler buckling
    │   │   ├── Flexural, shear, torsional components
    │   │   └── Effective length concepts (theory only)
    │   │
    │   ├── 1.3.2 Advanced Elastic Stability
    │   │   ├── Plates and shells
    │   │   ├── Koiter theory (asymptotic post-buckling)
    │   │   ├── Bifurcation vs limit points
    │   │   └── Imperfection sensitivity
    │   │
    │   ├── 1.3.3 Geometric Nonlinearity & Instability
    │   │   ├── Geometric stiffness matrix Kg
    │   │   ├── P–Δ and P–δ effects
    │   │   ├── Local–global interaction
    │   │   └── Thin-walled distortional modes
    │   │
    │   └── 1.3.4 Post-Buckling
    │       ├── Equilibrium path-following
    │       ├── Snap-through / snap-back
    │       └── Mode jumping
    │
    ├── 1.4 Structural Member Mechanics (Beams & Thin-Walled Sections)
    │   ├── 1.4.1 Beam Theory
    │   │   ├── Euler–Bernoulli beam theory
    │   │   ├── Timoshenko beam theory (shear deformation)
    │   │   ├── Shear correction factors
    │   │   ├── Beam-column interaction
    │   │   └── Generalized beam theory (GBT)
    │   │
    │   ├── 1.4.2 Shear Behaviour
    │   │   ├── Shear stress distribution
    │   │   ├── Shear flow in thin-walled/open/closed sections
    │   │   ├── Shear lag effects
    │   │   └── Web shear vs global shear behaviour
    │   │
    │   ├── 1.4.3 Torsion & Warping
    │   │   ├── Saint-Venant torsion
    │   │   ├── Vlasov warping torsion
    │   │   ├── Sectorial coordinates & bimoment
    │   │   └── Shear center & torsional stiffness
    │   │
    │   ├── 1.4.4 Plates, Shells & Elastic Foundations
    │   │   ├── Kirchhoff–Love thin plate theory
    │   │   ├── Mindlin–Reissner thick plate theory
    │   │   ├── Classical shell theory (Donnell/Love)
    │   │   ├── Analytical shell solutions (cylindrical, spherical)
    │   │   ├── Beams/plates on elastic foundations (Winkler)
    │   │   ├── Pasternak & Kerr models
    │   │   └── Soil–structure elastic continuum (non-geotechnical)
    │   │
    │   └── 1.4.5 FEM Aspects for Beams/Shells
    │       ├── Shear locking & remedies
    │       ├── Reduced/selective integration
    │       ├── Mixed formulations (EAS, ANS)
    │       └── Co-rotational beam elements
    │
    ├── 1.5 Structural Dynamics (Research Depth)
    │   ├── Free and forced vibration
    │   ├── Damping models (viscous, hysteretic, fractional)
    │   ├── Complex modes & non-proportional damping
    │   ├── Modal analysis, truncation & residual modes
    │   ├── Time integration (Newmark, HHT-α, generalized-α, WBZ, Wilson-θ)
    │   ├── Random vibration & PSD
    │   └── Operational modal analysis (OMA, SSI, EMD/HHT)
    │
    ├── 1.6 Finite Element Method (Research-Level FEM)
    │   ├── Linear FEM
    │   ├── Nonlinear FEM (material + geometric)
    │   ├── Mesh generation & refinement
    │   ├── Contact mechanics
    │   │   ├── Penalty method
    │   │   ├── Lagrange multipliers
    │   │   ├── Augmented Lagrangian
    │   │   └── Constraint enforcement algorithms
    │   ├── Mixed/hybrid formulations (u–p, EAS, reduced/selective integration)
    │   ├── Eigenvalue methods (Lanczos, subspace, Arnoldi)
    │   ├── Higher-order / spectral FEM; p/hp refinement
    │   ├── Isogeometric analysis (IGA)
    │   ├── XFEM & partition of unity
    │   └── Error estimation & adaptive mesh refinement
    │
    ├── 1.7 Numerical Methods
    │   ├── Linear & nonlinear solvers
    │   ├── Newton–Raphson variants
    │   ├── Line search & trust-region strategies
    │   ├── Arc-length & path-following methods
    │   ├── Time integration algorithms
    │   └── Optimization & model updating (gradient-based only)
    │
    └── 1.8 Classical Structural Analysis (Statics & Matrix Methods)
        ├── Determinate & indeterminate structures
        ├── Influence lines & envelopes
        ├── Force method (compatibility)
        ├── Displacement method (slope–deflection, moment distribution)
        ├── Matrix structural analysis (direct stiffness method)
        └── Energy methods (virtual work, unit load, Castigliano)