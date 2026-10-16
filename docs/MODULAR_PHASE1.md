# CONTROL CENTER — Phase 1 architecture

## Protected baseline

- Baseline source: `cade2e152c1044a2d9ce8050eef299ed4536c58b`.
- Embedded application version remains **1.0.14**. Older documentation labels disagree; this refactor does not relabel versions.
- Implementation branch: `refactor/modular-phase1`.
- No merge, production binary replacement, tag or release is authorized.
- `source/control_center_autonomous.py`, all of `source/modules/`, core database/schema/locking/path logic, resources, shared artwork, entry point, dependency requirements and PyInstaller specification are unchanged.

## Architecture

`main.py → ui.main_window → bootstrap / registry / workflows`

- `bootstrap.py`: service composition in original construction order.
- `contracts.py`: immutable module definitions and injected page callbacks.
- `registry.py`: explicit factories and navigation metadata. Page creation order and navigation order remain distinct and unchanged.
- `workflows.py`: original shift close → archive → backup coordination, with unchanged failure propagation.
- `ui/main_window.py`: composition, navigation, theme and common status handling.
- `ui/shell.py`, `ui/header.py`: extracted layout and header rendering.
- `features/{fines,refusals,receipts,daily_activity,periodicals,people,shifts,reports}`: cohesive existing pages, services and document engines.
- `infrastructure/`: document preview and backups.
- `shared/documents/`: existing document helpers.

The complete old/new file mapping is `modular-phase1-moves.json`. Old module paths are compatibility aliases to the **same module objects**, not duplicate implementations. Monkeypatching globals through an old import still affects canonical code. Active application imports use canonical paths.

Page cross-feature actions are injected `PageActions`; feature pages and archive dialogs no longer discover the main window or access sibling pages through `window().pages`. The top-level shift controller coordinates the original sequence of form saving, shift closure, report archive generation and refreshes. Database service APIs and all SQL are retained; this phase introduces no data migration or repository rewrite.

The autonomous application remains independent. Similar legacy engines are deliberately not merged because they implement a separate data model and workflow. No new duplication is introduced.

## Adding a future module

1. Add a cohesive package under `app/features/`; reuse existing infrastructure.
2. Define a `ModuleDefinition(key, title, icon, create_page)`.
3. Register it explicitly in `DEFAULT_MODULES`, or supply `(*DEFAULT_MODULES, definition)` when composing a window.
4. Declare new dependencies at composition time. Use injected callbacks for navigation and cross-page refreshes.
5. Add behavior and boundary tests. Feature modules must not import the entry point, main window, bootstrap or registry. Backend services must import without Qt.

A `None` navigation title keeps a module available without a sidebar button (the existing reports module). Duplicate identifiers fail before service creation. Existing mandatory modules are retained when extending the application. Dynamic plugin discovery and new business features are outside this phase.

## Validation method

The source baseline has **134 tests: 122 pass, 12 fail**. Their exact names and original assertion messages are retained in `modular-phase1-baseline.json`. Each separate transfer ran all 134 tests from `source/`, preserving the same outcome set. Tests that inspect source text follow the moved implementation; assertions about obsolete shell wiring were replaced by registry checks, without changing business expectations. Historical failed assertions remain failures.

New architecture tests check compatibility aliases, unchanged business/document ASTs (excluding imports), unchanged protected files, acyclic imports, backend independence, injected navigation, archive dialog callback inheritance, workflow ordering/failure propagation and adding a future module. See `source/tests/test_modular_architecture.py`.

`tools/compare_regressions.py` compares original and candidate JUnit outcomes. It rejects missing tests, changed historical outcomes, and any non-passing new test. It does not mark historical failures as passes or xfails. Run pytest from `source/`, as in the baseline; some historical tests depend on that working directory.

A separate isolated comparison captures the six existing pages in both themes, with fixed time and temporary SQLite data. It compares widget classes, names, visibility, enabled/checked states, text, choices, table headings, tabs and geometry. This is a structural Qt check, not a native Windows screenshot certification. `tools/capture_behavior_snapshot.py` additionally runs fixed imposition, payment, refusal and shift-report scenarios against both source trees: all 12 SQLite tables, the activity summary, XML content of 5 generated Word documents and the populated cells/styles/merged ranges of the daily Excel workbook must match. A Qt workflow test also fills the actual shift dialog, records a fine, closes the shift, checks generated reports and restarts against the same temporary database.

## Windows executable

`.github/workflows/modular-phase1-validation.yml` only validates this branch or an explicit dispatch. It checks the original source and modular source on Windows, compares their outcomes, builds using the unchanged `.spec`, and drives the real frozen EXE externally through UI Automation. Synthetic data is created in a temporary folder next to a copied test EXE. The driver starts a shift, exercises all six sidebar buttons, closes the shift and checks SQLite state/integrity and the generated daily Excel worksheet. It captures evidence and hashes the exact executable. It must fail if functional evidence is missing.

JSON/XML evidence is saved to the isolated `validation/control-center-modular-phase1` branch through a separate temporary Git index; the source branch and its index are not altered. This is the only job requiring contents write permission and it never writes main or production releases. Evidence records the exact source SHA and Actions run URL. Artifacts are test artifacts with 14-day retention. There are no release, tag, merge or production replacement steps. This workflow does not certify Office COM integration on a machine with Word/Excel, printing, or field acceptance.
