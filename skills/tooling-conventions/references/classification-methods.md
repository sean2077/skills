# Tool Classification Methods

Start with the independently invokable job: its consumers, owned state or artifact, failure and recovery behavior, and verification. These boundaries determine whether commands should aggregate, remain separate, or share private implementation.

| Evidence | Implication |
|---|---|
| One workflow with compatible transaction and recovery semantics | A shared entry or subcommands may simplify use. |
| Different domain ownership or meanings | Keep responsibilities and terminology explicit. |
| Human, CI, service, and installed consumers | Preserve the interface and path each consumer depends on. |
| Different state or artifact owners | Separate incompatible atomicity, rollback, and acceptance boundaries. |
| Production impact or independent recovery needs | Preserve the relevant safety and recovery entry points. |
| Generated, vendored, packaged, or installed assets | Follow their owning source, build, provenance, and distribution contracts. |

For example, compiling an image and rolling it out can share tooling without sharing a release boundary: installation may need health checks and rollback that a reproducible build does not. A service executable and a developer wrapper may share a library while retaining their separate interfaces.

Use the project's established placement when it fits. Compare alternatives for unresolved boundaries, including caller migration and verification cost. Keep consequential rationale in the existing design or task record.
