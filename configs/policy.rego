package circuitai.authz

import data.global_policy
import data.tenants

default allow := false

# The Kill Switch: Must pass Global Floor AND Tenant Ceiling
allow if {
    global_safety_ok
    tenant_safety_ok
}

# 1. Global Hard Floor: Reject if base safety is too low
global_safety_ok if {
    global_policy.min_safety_standard
    input.scores.non_maleficence >= global_policy.min_safety_standard
}

# 2. Tenant Ceiling: Total Risk Gap must be below threshold
tenant_safety_ok if {
    r := calculate_risk(input.company_id)
    r < tenants[input.company_id].threshold
}

# 3. The 5-Vector Calculator
calculate_risk(id) := r if {
    w := tenants[id].weights
    s := input.scores
    
    # R = (Distance from 1.0) * Weight
    r := ((1 - s.non_maleficence) * w.non_maleficence) + 
         ((1 - s.autonomy) * w.autonomy) +
         ((1 - s.beneficence) * w.beneficence) +
         ((1 - s.justice) * w.justice) +
         ((1 - s.explicability) * w.explicability)
}
