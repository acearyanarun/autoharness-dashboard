// Explanatory copy for known category ids. Presentation only: counts, labels and issue links
// always come from the data. Unknown ids (a future category) get a neutral fallback.

import type { Run } from "./contract";

export interface Explanation {
  summary: string;
  detail: (run: Run) => string;
  fix: string;
}

const EXPLANATIONS: Record<string, Explanation> = {
  missing_arbitrary: {
    summary: "An argument type has no kani::Arbitrary implementation.",
    detail: () =>
      "AutoHarness needs to produce a nondeterministic value for every argument. When at least one " +
      "argument's type neither implements kani::Arbitrary nor can have it derived (for example " +
      "trait objects, OS handles, or types with private invariants), the function is skipped. " +
      "Kani's reason text names the offending arguments and types.",
    fix: "Add Arbitrary implementations or value models for the listed types.",
  },
  generic_no_candidate: {
    summary: "Generic function with no concrete type that satisfies its bounds.",
    detail: () =>
      "For a generic function, AutoHarness searches for a concrete instantiation: primitive " +
      "candidates plus types that implement the required traits. If none satisfies every trait " +
      "bound, it is skipped. Today the same message also covers searches that stopped at the " +
      "query limit (tracked in kani#4877).",
    fix: "Widen the candidate search or make the skip reason distinguish its causes.",
  },
  const_generic_unsupported: {
    summary: "Const generic parameter AutoHarness cannot instantiate.",
    detail: () =>
      "AutoHarness substitutes a fixed value only for usize const generics. Functions with other " +
      "const parameter types (often i32 immediates in x86 SIMD intrinsics) are skipped, as are " +
      "usize const generics guarded by a `const {}` block that might reject the substituted value.",
    fix: "Support non-usize const generic parameters (kani#4876).",
  },
  requires_bounded_arguments: {
    summary: "Arguments that can only be generated with a size bound.",
    detail: (run) =>
      "Slices, &str, &CStr and BoundedArbitrary containers can be generated only up to a bound, " +
      "which requires --bounded-arguments. " +
      (run.flags.bounded_arguments
        ? "This run had --bounded-arguments enabled, so these are functions that still need it."
        : "This run did not enable --bounded-arguments, so these skips come from the run's " +
          "configuration rather than a Kani limitation; enabling the flag generates harnesses for them."),
    fix: "Expected behaviour without the flag; track bounded-argument support here.",
  },
  no_body: {
    summary: "No function body visible to Kani.",
    detail: () =>
      "Kani verifies function bodies. Functions without one, mostly compiler intrinsics, cannot " +
      "get a harness. This is expected behaviour; remaining gaps are handled with models or stubs.",
    fix: "Expected behaviour; add models or stubs for intrinsics worth covering.",
  },
};

export function explain(id: string): Explanation {
  return (
    EXPLANATIONS[id] ?? {
      summary: "No description for this category yet.",
      detail: () => "This category is defined in the dataset but has no explanatory text in this dashboard.",
      fix: "See the umbrella issue.",
    }
  );
}
