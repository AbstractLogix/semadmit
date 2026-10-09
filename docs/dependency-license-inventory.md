# Dependency and License Inventory

**Status: partial release evidence.** This inventory records the exact Haskell dependency lock and the Python build backend used for this validation. It does not approve redistribution or replace an owner review of license obligations.

## Evidence Source

- Project baseline: `46b81c7d1429dc645efafdafcfac35b584ef38b9`.
- Haskell graph: 71 exact package versions in `cabal.project.freeze`, SHA-256 `9d325355033734244fdea95c0c2ebb92d2c81a7e9e748c528efc0184c99122ba`.
- Hackage index state: `2026-09-16T00:00:00Z`.
- 69 packages were checked from source archives retrieved at that index state. Each declared `license` value and `license-file(s)` path came from its Cabal package description. Each declared license file was present. No `NOTICE` file was present in those 69 package source archives.
- `ghc-prim-0.13.1` and `rts-1.0.3` have no source archive at the pinned Hackage index state. The GHC 9.14.1 package database declares `BSD-3-Clause` for both. Their source license text and notices were not checked in this run.
- The Cabal description format defines the `license` and `license-files` fields. These values are recorded as published; older values such as `BSD3` and `BSD2` are not rewritten here. See the [Cabal package description specification](https://github.com/haskell/cabal/blob/master/doc/cabal-package-description-file.rst).

The inventory checks metadata and the presence of declared license files. It does not compare each license text with its upstream copyright history or decide whether every redistribution condition is met. The missing source evidence for `ghc-prim` and `rts` keeps this gate open for a Haskell binary release.

## Haskell Locked Graph

| Package | Version | Cabal license field | Metadata and file check |
| --- | --- | --- | --- |
| QuickCheck | 2.18.0.0 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| StateVar | 1.2.2 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| aeson | 2.2.5.1 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| ansi-terminal | 1.1.5 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| ansi-terminal-types | 1.1.3 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| array | 0.5.8.0 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| assoc | 1.1.1 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| base | 4.22.0.0 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| base-orphans | 0.9.4 | MIT | Hackage; `LICENSE` present; no `NOTICE` |
| bifunctors | 5.6.3 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| binary | 0.8.9.3 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| bytestring | 0.12.2.0 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| character-ps | 0.1 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| colour | 2.3.7 | MIT | Hackage; `LICENSE` present; no `NOTICE` |
| comonad | 5.0.10 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| containers | 0.8 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| contravariant | 1.5.6 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| cryptohash-sha256 | 0.11.102.1 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| data-fix | 0.3.4 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| deepseq | 1.5.1.0 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| directory | 1.3.10.0 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| distributive | 0.6.3 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| dlist | 1.0 | BSD3 | Hackage; `license.md` present; no `NOTICE` |
| exceptions | 0.10.11 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| file-io | 0.1.5 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| filepath | 1.5.4.0 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| ghc-boot-th | 9.14.1 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| ghc-internal | 9.1401.0 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| ghc-prim | 0.13.1 | BSD-3-Clause | GHC 9.14.1 package database only; source and notice not checked |
| hashable | 1.5.1.0 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| indexed-traversable | 0.1.5 | BSD2 | Hackage; `LICENSE` present; no `NOTICE` |
| indexed-traversable-instances | 0.1.2.1 | BSD2 | Hackage; `LICENSE` present; no `NOTICE` |
| integer-conversion | 0.1.1 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| integer-logarithms | 1.0.5 | MIT | Hackage; `LICENSE` present; no `NOTICE` |
| mtl | 2.3.1 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| network-uri | 2.6.4.2 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| optparse-applicative | 0.19.0.0 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| os-string | 2.0.8 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| parsec | 3.1.18.0 | BSD2 | Hackage; `LICENSE` present; no `NOTICE` |
| pretty | 1.1.3.6 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| prettyprinter | 1.7.2 | BSD2 | Hackage; `LICENSE.md` present; no `NOTICE` |
| prettyprinter-ansi-terminal | 1.1.4 | BSD2 | Hackage; `LICENSE.md` present; no `NOTICE` |
| primitive | 0.9.1.0 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| process | 1.6.26.1 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| random | 1.3.1 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| rts | 1.0.3 | BSD-3-Clause | GHC 9.14.1 package database only; source and notice not checked |
| scientific | 0.3.8.1 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| semialign | 1.4 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| semigroupoids | 6.0.2 | BSD2 | Hackage; `LICENSE` present; no `NOTICE` |
| splitmix | 0.1.3.2 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| stm | 2.5.3.1 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| strict | 0.5.1 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| tagged | 0.8.10 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| tasty | 1.5.4 | MIT | Hackage; `LICENSE` present; no `NOTICE` |
| template-haskell | 2.24.0.0 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| text | 2.1.3 | BSD-2-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| text-iso8601 | 0.1.1.2 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| text-short | 0.1.6.1 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| th-abstraction | 0.7.2.0 | ISC | Hackage; `LICENSE` present; no `NOTICE` |
| th-compat | 0.1.7 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| these | 1.2.1 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| time | 1.15 | BSD-2-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| time-compat | 1.9.9 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| transformers | 0.6.1.2 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| transformers-compat | 0.8 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| unix | 2.8.8.0 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| unordered-containers | 0.2.21 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| uuid-types | 1.0.6.1 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| vector | 0.13.2.0 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |
| vector-stream | 0.1.0.1 | BSD3 | Hackage; `LICENSE` present; no `NOTICE` |
| witherable | 0.5 | BSD-3-Clause | Hackage; `LICENSE` present; no `NOTICE` |

## Python Build Dependencies and Package Contents

- Python runtime dependencies: none.
- Build backend: `setuptools==84.0.0`, pinned in `clients/python/pyproject.toml`. It is build-only and declares MIT in the upstream [Setuptools 84.0.0 metadata](https://github.com/pypa/setuptools/blob/v84.0.0/pyproject.toml). Its license file is in the [Setuptools 84.0.0 source](https://github.com/pypa/setuptools/blob/v84.0.0/LICENSE).
- Build frontend used here: uv 0.11.31. It is not bundled in the Semadmit wheel.
- The Python sdist and wheel include Semadmit's `LICENSE`. The wheel metadata declares `License-Expression: Apache-2.0`; it contains the nine package modules and no test package.
- The Haskell `cabal sdist` archive includes the project `LICENSE`, source, and tests. It does not include a `NOTICE` file.

The [Apache License 2.0 text](https://www.apache.org/licenses/LICENSE-2.0.html) requires distribution of a license copy. If a source package includes a `NOTICE` file, applicable attribution notices must also be retained. This check found no `NOTICE` file in the 69 Hackage source archives reviewed. The two GHC package entries still need source-level notice review before a Haskell binary is distributed.
