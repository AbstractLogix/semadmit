# Dependency and License Inventory

**Status: evidence recorded; redistribution approval open.** This inventory records the exact Haskell dependency lock, archive digests, source locations, declared licenses, and inspected notice files. It does not approve redistribution or replace an owner review of license obligations.

## Evidence Source

- Project baseline: `b4e1f85ccc8bc56de8f4b12529cfc4e110ee21c7`.
- Haskell graph: 71 exact package versions in `cabal.project.freeze`, SHA-256 `9d325355033734244fdea95c0c2ebb92d2c81a7e9e748c528efc0184c99122ba`.
- Effective Cabal Hackage index state: `2026-09-15T22:55:42Z`, from `cabal.project.freeze`. The `cabal.project` file says `2026-09-16T00:00:00Z`, but Cabal applies `cabal.project.freeze` after `cabal.project`; see the [Cabal project configuration order](https://github.com/haskell/cabal/blob/master/doc/cabal-project-description-file.rst#L204-L210).
- All 69 locked Hackage archives match their `package.json` target SHA-256 and size in the Cabal-managed local Hackage index/cache. The current `01-index.tar` digest is `63acf6536e0cdfe6aca24f8b018006dafd32e1df45f1d82c817260f2dd8f28da`. A fresh Hackage download of `aeson-2.2.5.1` also matches its target hash. The per-package URLs, hashes, sizes, declared licenses, license-file hashes, source repositories, and separate `NOTICE` file results are in [dependency-provenance.json](dependency-provenance.json).
- The index target metadata is read from the current Cabal-managed index cache. This report does not claim that the whole index tar is a historical snapshot at the freeze timestamp or independently re-validate its signing key chain. Hackage package target metadata records the package archive hash and size; see the [Hackage security design](https://github.com/haskell/hackage-security/blob/master/README.md#targets).
- All 69 declared Cabal license files were present in the checked source archives. No separate `NOTICE` file was found in those archives. This check does not review every source file for embedded copyright or attribution notices.
- Three Hackage package descriptions do not declare a source repository: `base-4.22.0.0`, `colour-2.3.7`, and `strict-0.5.1`. Their source repository remains unestablished here; no URL is inferred.
- `ghc-prim-0.13.1` and `rts-1.0.3` are included with the exact GHC 9.14.1 toolchain source distribution, not the Hackage lock. The signed source archive SHA-256 is `2a83779c9af86554a3289f2787a38d6aa83d00d136aa9f920361dd693c101e77`. Both archive signatures verify under the key published by the [GHC 9.14.1 download page](https://ghc.gitlab.haskell.org/homepage/download_ghc_9_14_1.html); the local GPG trust database does not certify that key.
- `ghc-prim` declares BSD-3-Clause and includes its `LICENSE`, which contains the GHC notice and Haskell 98 report notice. `rts` declares BSD-3-Clause but has no `license-file` field. Its enclosing GHC source archive includes the GHC `LICENSE`; `rts` also contains inline xxHash BSD-2-Clause terms, the LLVM license text, and the Free Software Foundation's unlimited-permission notice in its generated `configure` script. Vendored Closure Library code in `rts/js/md5.js` has an Apache-2.0 header, but no separate Apache license copy or `NOTICE` file was found under `rts`. The assessed Semadmit native Linux executable and Cabal source archive do not contain this JavaScript file. The Apache license-copy issue applies to a distribution that includes the Closure work. The notice bundle for the Haskell executable's linked libraries and runtime remains incomplete.
- The Cabal description format defines the `license` and `license-files` fields. These values are recorded as published; older values such as `BSD3` and `BSD2` are not rewritten here. See the [Cabal package description specification](https://github.com/haskell/cabal/blob/master/doc/cabal-package-description-file.rst).

The inventory checks package metadata, archive digests, and declared license-file presence. It does not compare every license text with its upstream copyright history or decide whether every redistribution condition is met. No Haskell binary is currently a Semadmit release artifact. A future Haskell executable release remains blocked on a complete notice bundle and owner approval. This inventory is not legal approval.

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
| ghc-prim | 0.13.1 | BSD-3-Clause | GHC 9.14.1 source archive; `libraries/ghc-prim/LICENSE` present with GHC and Haskell 98 notices |
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
| rts | 1.0.3 | BSD-3-Clause | GHC 9.14.1 source archive; no `license-file` field; root GHC license and reviewed inline notices present; Closure Apache copy applies if that JS work is redistributed |
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
- Build backend: `setuptools==84.0.0`, pinned in `clients/python/pyproject.toml`. Its exact wheel URL and SHA-256 are in [dependency-provenance.json](dependency-provenance.json). The wheel metadata declares MIT and includes its license file. Setuptools is build-only and is not included in Semadmit's Python artifacts. See the [Setuptools 84.0.0 metadata](https://github.com/pypa/setuptools/blob/v84.0.0/pyproject.toml) and [license file](https://github.com/pypa/setuptools/blob/v84.0.0/LICENSE).
- Build frontend used here: uv 0.11.31. It is not bundled in the Semadmit wheel.
- The Python sdist and wheel include Semadmit's `LICENSE`. The wheel metadata declares `License-Expression: Apache-2.0`; it contains the nine package modules and no test package.
- The Haskell `cabal sdist` archive includes the project `LICENSE`, source, and tests. It does not include a `NOTICE` file.

The [Apache License 2.0, section 4](https://www.apache.org/licenses/LICENSE-2.0.txt) requires a license copy when the covered work is distributed. Its NOTICE-file condition applies when the source work includes a NOTICE file. The Python package artifacts contain Semadmit's Apache-2.0 license. The Hackage archives reviewed contain their declared license files but no separate `NOTICE` files. The GHC archive contains the Apache-licensed Closure JavaScript source but no separate Apache license copy under `rts`. The Semadmit native Linux executable and source archive assessed here do not contain that file. The project must not publish a Haskell executable until the owner approves a complete notice bundle for the code it includes.
