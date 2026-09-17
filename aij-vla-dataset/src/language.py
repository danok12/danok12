"""Разбор исходной инструкции эпизода и её декомпозиция на шаги.

Инструкции в робототехнических датасетах — короткие императивы
(«pick up the alphabet soup and place it in the basket»), поэтому используется
детерминированный лексический разбор, а не языковая модель.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .kinematics import (
    PHASE_ALIGN,
    PHASE_APPROACH,
    PHASE_GRASP,
    PHASE_IDLE,
    PHASE_INTERACT,
    PHASE_LIFT,
    PHASE_RELEASE,
    PHASE_RETREAT,
    PHASE_TRANSPORT,
)

# Многословные глаголы — раньше однословных: порядок важен при матчинге.
VERB_PHRASES: list[tuple[str, str]] = [
    ("pick up", "pick_place"),
    ("put down", "pick_place"),
    ("turn on", "toggle"),
    ("turn off", "toggle"),
    ("take out", "pick_place"),
    ("put away", "pick_place"),
    ("push down", "push"),
    ("pull out", "open"),
    ("place", "pick_place"),
    ("put", "pick_place"),
    ("pick", "pick_place"),
    ("take", "pick_place"),
    ("grasp", "pick_place"),
    ("grab", "pick_place"),
    ("lift", "pick_place"),
    ("drop", "pick_place"),
    ("stack", "pick_place"),
    ("insert", "pick_place"),
    ("move", "push"),
    ("push", "push"),
    ("slide", "push"),
    ("pull", "open"),
    ("open", "open"),
    ("close", "close"),
    ("shut", "close"),
    ("press", "toggle"),
    ("flip", "toggle"),
    ("rotate", "push"),
    ("turn", "toggle"),
    ("pour", "pick_place"),
    ("wipe", "push"),
    ("fold", "push"),
    ("knock", "push"),
    ("separate", "push"),
    ("sweep", "push"),
]

TARGET_PREPS: list[str] = [
    " into the ",
    " onto the ",
    " inside the ",
    " next to the ",
    " on top of the ",
    " in front of the ",
    " to the left of the ",
    " to the right of the ",
    " close to the ",
    " near the ",
    " beside the ",
    " behind the ",
    " under the ",
    " over the ",
    " above the ",
    " in the ",
    " on the ",
    " at the ",
    " to the ",
    " from the ",
    " into ",
    " onto ",
    " in ",
    " on ",
    " to ",
]

CLAUSE_SPLIT = re.compile(r"\s*(?:,\s*)?(?:and then|then|and)\s+", flags=re.IGNORECASE)
ARTICLES = ("the ", "a ", "an ")


def _strip_article(text: str) -> str:
    out = text.strip()
    for article in ARTICLES:
        if out.lower().startswith(article):
            return out[len(article) :].strip()
    return out


@dataclass
class Clause:
    verb: str
    kind: str
    obj: str
    prep: str = ""
    target: str = ""


@dataclass
class ParsedInstruction:
    text: str
    clauses: list[Clause] = field(default_factory=list)

    @property
    def kind(self) -> str:
        for clause in self.clauses:
            if clause.kind in {"pick_place", "open", "close", "toggle", "push"}:
                return clause.kind
        return "generic"

    @property
    def obj(self) -> str:
        for clause in self.clauses:
            if clause.obj:
                return clause.obj
        return "the object"

    @property
    def target(self) -> str:
        for clause in reversed(self.clauses):
            if clause.target:
                return clause.target
        return ""

    @property
    def prep(self) -> str:
        for clause in reversed(self.clauses):
            if clause.target and clause.prep:
                return clause.prep
        return "at"

    @property
    def obj_short(self) -> str:
        return _strip_article(self.obj)

    @property
    def target_short(self) -> str:
        return _strip_article(self.target)

    @property
    def is_valid(self) -> bool:
        return bool(self.text.strip()) and bool(self.clauses)


def parse_instruction(text: str) -> ParsedInstruction:
    raw = (text or "").strip().rstrip(".").strip()
    parsed = ParsedInstruction(text=raw)
    if not raw:
        return parsed
    for piece in CLAUSE_SPLIT.split(raw):
        clause = _parse_clause(piece.strip())
        if clause is not None:
            parsed.clauses.append(clause)
    if not parsed.clauses:
        parsed.clauses.append(Clause(verb="", kind="generic", obj=raw))
    _propagate_pronouns(parsed)
    return parsed


def _parse_clause(text: str) -> Clause | None:
    if not text:
        return None
    lowered = text.lower()
    verb, kind, rest = "", "generic", text
    for phrase, phrase_kind in VERB_PHRASES:
        if lowered.startswith(phrase + " "):
            verb, kind = phrase, phrase_kind
            rest = text[len(phrase) :].strip()
            break
    obj, prep, target = rest, "", ""
    padded = f" {rest} "
    for candidate in TARGET_PREPS:
        pos = padded.lower().find(candidate)
        if pos > 0:
            obj = padded[:pos].strip()
            prep_words = candidate.strip().split()
            keep_article = prep_words[-1] == "the"
            prep = " ".join(prep_words[:-1]) if keep_article else " ".join(prep_words)
            target = padded[pos + len(candidate) :].strip()
            if keep_article:
                target = f"the {target}"
            break
    return Clause(verb=verb, kind=kind, obj=obj.strip(), prep=prep.strip(), target=target.strip())


def _propagate_pronouns(parsed: ParsedInstruction) -> None:
    """«place it in the basket» — подставляем объект из предыдущего клауза."""
    last_obj = ""
    for clause in parsed.clauses:
        if clause.obj.lower() in {"it", "them", "this", "that", ""} and last_obj:
            clause.obj = last_obj
        elif clause.obj:
            last_obj = clause.obj


# --------------------------------------------------------------- декомпозиция
def decompose(parsed: ParsedInstruction) -> list[str]:
    """Список шагов выполнения инструкции на естественном языке."""
    obj = parsed.obj_short or "the object"
    target = parsed.target_short
    prep = parsed.prep or "at"
    kind = parsed.kind
    if kind == "pick_place":
        steps = [
            f"move the gripper above the {obj}",
            f"lower the open gripper around the {obj}",
            f"close the gripper on the {obj}",
            f"lift the {obj} off the surface",
        ]
        if target:
            into = {"in": "into", "on": "onto", "at": "to"}.get(prep, prep)
            steps.append(f"carry the {obj} toward the {target}")
            steps.append(f"lower the {obj} {into} the {target}")
        steps.append(f"open the gripper to release the {obj}")
        steps.append("withdraw the arm")
        return steps
    if kind in {"open", "close"}:
        verb = "pull" if kind == "open" else "push"
        return [
            f"move the gripper to the handle of the {obj}",
            f"close the gripper on the handle of the {obj}",
            f"{verb} the {obj} until it is fully {kind}ed",
            "release the handle",
            "withdraw the arm",
        ]
    if kind == "toggle":
        return [
            f"move the gripper to the {obj}",
            f"press or turn the {obj}",
            "check that the state has changed",
            "withdraw the arm",
        ]
    if kind == "push":
        tail = f" {prep} the {target}" if target else ""
        return [
            f"move the gripper next to the {obj}",
            f"make contact with the {obj}",
            f"push the {obj}{tail}",
            "withdraw the arm",
        ]
    return [f"approach the {obj}", f"act on the {obj}", "withdraw the arm"]


_PHASE_STEP_INDEX: dict[str, dict[str, int]] = {
    "pick_place": {
        PHASE_IDLE: 0,
        PHASE_APPROACH: 1,
        PHASE_GRASP: 2,
        PHASE_LIFT: 3,
        PHASE_TRANSPORT: 4,
        PHASE_ALIGN: 5,
        PHASE_RELEASE: 6,
        PHASE_RETREAT: 7,
        PHASE_INTERACT: 4,
    },
    "open": {
        PHASE_IDLE: 0,
        PHASE_APPROACH: 0,
        PHASE_GRASP: 1,
        PHASE_LIFT: 2,
        PHASE_TRANSPORT: 2,
        PHASE_ALIGN: 2,
        PHASE_INTERACT: 2,
        PHASE_RELEASE: 3,
        PHASE_RETREAT: 4,
    },
    "toggle": {
        PHASE_IDLE: 0,
        PHASE_APPROACH: 0,
        PHASE_GRASP: 1,
        PHASE_INTERACT: 1,
        PHASE_LIFT: 1,
        PHASE_TRANSPORT: 1,
        PHASE_ALIGN: 1,
        PHASE_RELEASE: 2,
        PHASE_RETREAT: 3,
    },
    "push": {
        PHASE_IDLE: 0,
        PHASE_APPROACH: 0,
        PHASE_GRASP: 1,
        PHASE_INTERACT: 2,
        PHASE_LIFT: 2,
        PHASE_TRANSPORT: 2,
        PHASE_ALIGN: 2,
        PHASE_RELEASE: 2,
        PHASE_RETREAT: 3,
    },
}


def step_index_for_phase(parsed: ParsedInstruction, phase: str, n_steps: int) -> int:
    table = _PHASE_STEP_INDEX.get(parsed.kind, _PHASE_STEP_INDEX["push"])
    idx = table.get(phase, 0)
    if parsed.kind == "pick_place" and not parsed.target_short:
        # Без адресата шаги «carry»/«lower» отсутствуют — сдвигаем индексы.
        idx = max(0, idx - 2) if idx >= 4 else idx
    return int(min(max(idx, 0), max(0, n_steps - 1)))


def subtask_for_phase(parsed: ParsedInstruction, phase: str) -> str:
    steps = decompose(parsed)
    return steps[step_index_for_phase(parsed, phase, len(steps))]


def next_subtask_for_phase(parsed: ParsedInstruction, phase: str) -> str:
    steps = decompose(parsed)
    idx = step_index_for_phase(parsed, phase, len(steps))
    return steps[idx + 1] if idx + 1 < len(steps) else "the task is finished, nothing remains"


def object_mentions(parsed: ParsedInstruction) -> list[str]:
    out = [parsed.obj_short]
    if parsed.target_short:
        out.append(parsed.target_short)
    return [x for x in out if x]
