% Prolog-style rules example (v1) — minimal starter set for pipeline validation.
% See spec/prolog_rule_grammar.md and sphere/prolog_logic/.

entropy_low(true).
coverage_ok(true).
curvature_high(true).

structural_monotony :- entropy_low(true), coverage_ok(true).
rhetorical_instability :- curvature_high(true).
