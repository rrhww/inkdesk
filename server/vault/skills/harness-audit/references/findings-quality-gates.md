# Findings Quality Gates

A Finding is eligible only when all checks pass:

1. It names an observed consequence, not a stylistic preference.
2. Its evidence IDs exist in the supplied Evidence Bundle.
3. It identifies the smallest practical owner and bounded repair scope.
4. It names a concrete expected artifact or observable outcome.
5. It includes at least one executable or inspectable verifier.
6. Severity follows consequence; confidence follows evidence completeness.
7. It does not expose credentials, private paths, or unredacted personal data.

Freeze eligible Findings before calculating dimension scores, support tracks, or priority moves.
