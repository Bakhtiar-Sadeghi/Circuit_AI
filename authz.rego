package circuitai.authz

import rego.v1

default allow := false

# Rule 1: Managers can invest up to $1,000
allow if {
    input.user_role == "manager"
    input.action == "invest"
    input.amount <= 1000
}

# Rule 2: CEO has an unlimited budget
allow if {
    input.user_role == "ceo"
    input.action == "invest"
}
