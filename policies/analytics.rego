package analytics
import rego.v1

default allow := false

deny contains "unsupported_stage" if { not input.stage in {"pre", "post"} }
deny contains "untrusted_input" if { input.guard_passed != true }
deny contains "write_forbidden" if { input.read_only != true }
deny contains "no_source_table" if { count(input.tables) == 0 }
deny contains "table_not_allowed" if {
    some table in input.tables
    not table in {"orders", "sales_lines", "customer_summary"}
}
deny contains "row_cap_required" if { input.row_cap != 200 }
deny contains "attempt_limit" if { not input.attempt in {1, 2, 3} }
deny contains code if {
    input.stage == "post"
    some code in input.result_violations
}

allow if {
    input.stage in {"pre", "post"}
    input.guard_passed == true
    input.read_only == true
    count(input.tables) > 0
    input.row_cap == 200
    input.attempt in {1, 2, 3}
    is_array(input.result_violations)
    count(deny) == 0
}

decision := {"allow": allow, "reasons": sort([code | some code in deny])}
