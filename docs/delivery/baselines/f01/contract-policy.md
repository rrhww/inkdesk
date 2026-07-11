# F01 Contract Policy

F01 protects externally observable behavior while allowing implementation refactoring. OpenAPI is the complete HTTP shape authority. `behavior-contracts.json` records state transitions and side effects that OpenAPI cannot express.

Committed contracts contain only synthetic or structural data. They must not contain credentials, cookies, local host URLs, absolute paths, live record content, dump files, archives, local manifests, or test logs.

JSON object keys are canonicalized in UTF-8 with LF line endings. Arrays retain their product-defined order unless the exporter explicitly sorts catalog results whose source ordering is non-semantic.

Schema compatibility digests include application tables, column types and nullability/defaults, primary/unique/foreign keys, `ON DELETE` behavior, and index method/elements. Constraint and index physical names are diagnostic only.

Known issues are exceptions for precisely identified, time-bounded deviations. Every issue needs an ID, bounded scope, exact matcher, evidence, reason, disposition, observation time, expiry, and next-plan impact. Broad regexes, suite-wide exemptions, and non-expiring exceptions are invalid.

`PASS` means all required checks passed. `PASS_WITH_KNOWN_ISSUES` is valid only when every failing result exactly matches a current issue. Any unregistered failure, unsafe restore condition, incomplete evidence, changed source fingerprint, or failed service recovery is `FAIL`.
