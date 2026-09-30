# Editor key lifecycle: scoped draft

Owner: Kepler; joint Toad TC1/T9 integration owner: Heisenberg227.
No open Textual PR overlapped this input boundary at claim time.

## Actual failing path

Default Core000/Toad173/Textual650/nativee36, actual retained 41 MB
`nra-architecture`, existing child `nra-domain-mapping`, actual isolated
st/Xvfb and an isolated SQLite copy of Toad UI state. No provider calls,
prompt submission, public mutation or native input replay.

Raw evidence:
`/home/ts/.cache/agent-scratch/toad-editor-focus-227-20260930-run02/capture`.
The 45.946-second physical journey completed typing, history selection,
child/parent tab return, channel opening and agent return. Native focused
editor identities are correct at each phase. `abcdef` followed by Left,
Left, Backspace, Delete, Right produced **abcef**, not **abcf**, in both
agent and channel editors. The physical edited frame shows the Help panel
opening. Original native source hashes and process identities are unchanged;
recorder cleanup has no remaining owned processes or errors.

Installed st binary SHA256
`a3cd85021357789a10f936690671be8dad25c620eb580ffb6f8e43e3620570c2`
matches `/home/ts/programs/st/st`. Its source configuration sends CSI P for
Delete in normal keypad mode and CSI 3~ in application keypad mode. The
actual installed Textual parser maps CSI P to F1 and CSI 3~ to Delete.
Linux full-screen and inline application startup currently never enter
application keypad mode. No focus mirror or editor-specific key policy is
needed to explain this failure.

## Intended ownership closure

The terminal driver owns entry and retirement of application keypad mode.
Share its native enter/leave operations through the existing Driver owner;
both Linux full-screen and inline lifecycle consumers call that contract.
Suspension/resumption already delegates to the same stop/start methods.
Do not remap F1, add a TERM string switch, create a focus flag, or patch each
editor. Keep the canonical parser and native Screen focus authority intact.
This is an IMPL-13 lifecycle closure, not a compatibility reader.

[XTerm control sequences](https://invisible-island.net/xterm/ctlseqs/ctlseqs.html)
declares ESC = for application keypad and ESC > for normal keypad.

Source work and actual affected installed physical acceptance are pending.
Passing a parser probe does not establish user readiness. Backspace and
Left/Right passed this bounded run; intermittent loss of those keys is not
reproduced and must not be claimed fixed by this Delete repair.

Counterevidence retained: run01 omitted the key script and recorded only
startup/idle; it proves no editing behavior. The corrected run02 supplied
the script and required every physical phase marker.
