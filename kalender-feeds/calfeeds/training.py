"""Treningsmodell: lager en rullerende plan fra mål (konkurranser) og dagens form.

Modellen er regler, ikke skjønn, så den kan testes og gir samme plan for samme data:

* Planen bygges bakover fra konkurransedatoene: grunnfase, spesifikk fase, nedtrapping i
  konkurranseuka og en rolig uke etterpå.
* Ukas treningstid (timer) øker ca. 8 % per uke, med en lett uke (-25 %) når det har gått tre
  vanlige uker. Løpevolumet øker saktere (maks 12 % over siste vanlige uke), resten av tiden tas av
  SkiErg, ski og styrke, som er skånsommere. Etter en pause starter planen med tre rolige uker.
* Hver lett uke har en test (SkiErg, 5 km, styrke i rotasjon), så forbedringen måles.
* Intensitet kommer først etter noen uker med vanlig løping, og aldri i lette uker,
  konkurranseuker eller hvis status sier «hold_intensity».
* Perioder med tilgang til ski (data/trening.json, «availability») gir ski i stedet for SkiErg
  og rolig løping, og en lang ski-uke uten lett uke.
* Øktene er ikke bundet til fast ukedag. De legges så harde økter ikke havner på dagene
  rett før eller etter hverandre, beinøkt ikke dagen før kvalitet eller langtur, langturen i
  helga, og minst én hviledag.

Dagens form (timer, løpevolum, pause, skade) oppdateres i data/trening.json, hentet fra Strava.
Kalenderen får bare navnet på økten. Varighetene er til planleggingen her.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta

RETURN_HOURS = [5.5, 6.5, 7.5]
RETURN_RUN_MIN = [20, 25, 30]   # per gå/løp-økt, to økter i uka
HOURS_GROWTH = 1.08
DELOAD = 0.75
RUN_RAMP = 1.12
HOURS_CAP = {"base": 11.5, "build_ski": 14.5, "build_half": 13.5}
CAMP_BOOST = 1.10
CAMP_MIN_DAYS = 5
LONG_MIX = "Langtur: løping + SkiErg"
PHASE_HOURS_FACTOR = {"taper": 0.55, "recovery": 0.4}
RUN_SHARE = {"base": 0.55, "build_ski": 0.30, "build_half": 0.65}
SPEC_WEEKS = {"ski": 8, "halvmaraton": 3, "run": 3, "maraton": 12}
STRENGTH_MIN = 195
TESTS = ["SkiErg", "5 km", "Styrke"]
FRIDAY = ["Pull", "Arms", "Upper", "Pull", "Push", "Arms"]
PHASE_NAME = {"return": "Tilbake etter pause", "base": "Grunnfase", "build_ski": "Ski-spesifikk fase",
              "taper": "Konkurranseuke", "recovery": "Rolig uke etter konkurranse",
              "build_half": "Halvmaraton-spesifikk fase"}
HARD = {"long", "quality", "legs"}
CARDIO = {"run", "long", "quality", "aerobic"}
PAIR = {("long", "quality"): 35, ("legs", "long"): 60, ("legs", "quality"): 45,
        ("quality", "legs"): 20, ("long", "legs"): 30, ("quality", "long"): 20}
I_STR, I_RUN, I_SKI = "🏋️", "🏃", "⛷️"
QUALITY_RUN = ("4x4", "Tempo", "Bakkeintervaller", "Halvmaraton-fart")


def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


@dataclass(frozen=True)
class Goal:
    id: str
    name: str
    kind: str
    day: date
    target: str = ""

    @property
    def race_week(self) -> date:
        return monday(self.day)

    @property
    def spec_weeks(self) -> int:
        return SPEC_WEEKS.get(self.kind, 4)


@dataclass(frozen=True)
class Window:
    start: date
    end: date
    modes: tuple
    note: str = ""

    def days_in(self, mon: date) -> int:
        return sum(1 for i in range(7) if self.start <= mon + timedelta(days=i) <= self.end)


@dataclass(frozen=True)
class Week:
    monday: date
    number: int
    phase: str
    deload: bool
    hours: float
    run_minutes: int
    weeks_to_race: int | None
    since_return: int
    goal: Goal | None
    camp: bool
    test: str | None


@dataclass(frozen=True)
class Spec:
    title: str
    icon: str
    kind: str      # strength | legs | run | long | quality | aerobic
    minutes: int

    @property
    def hard(self) -> bool:
        return self.kind in HARD


@dataclass(frozen=True)
class Session:
    day: date
    title: str
    icon: str
    kind: str
    minutes: int


def goals_from(data: list[dict]) -> list[Goal]:
    goals = [Goal(g["id"], g["name"], g["type"], date.fromisoformat(g["date"]), g.get("target_time", ""))
             for g in data if g.get("active", True)]
    return sorted(goals, key=lambda g: g.day)


def windows_from(data: list[dict]) -> list[Window]:
    return [Window(date.fromisoformat(w["from"]), date.fromisoformat(w["to"]), tuple(w.get("modes", ["ski"])), w.get("note", ""))
            for w in data]


def _phase(mon: date, goals: list[Goal]):
    for g in goals:
        if mon > g.race_week + timedelta(days=7):
            continue
        if mon == g.race_week + timedelta(days=7):
            return "recovery", None, g
        to = (g.race_week - mon).days // 7
        if to == 0:
            return "taper", 0, g
        if to <= g.spec_weeks:
            return ("build_ski" if g.kind == "ski" else "build_half"), to, g
        return "base", to, g
    return "base", None, None


def build_weeks(plan_start: date, last: date, goals: list[Goal], status: dict, windows=()) -> list[Week]:
    weeks: list[Week] = []
    returning = 3 if status.get("return_to_run") else 0
    prog = float(status.get("weekly_hours_recent", 6.0))
    anchor = max(float(status.get("weekly_run_km_recent", 8)) * 6, 60.0)  # minutter løping per uke
    streak = tests_done = 0
    mon, number = monday(plan_start), 1
    while mon <= last:
        phase, to, goal = _phase(mon, goals)
        camp = any(w.days_in(mon) >= CAMP_MIN_DAYS and "ski" in w.modes for w in windows)
        since = number - 1 - returning
        if number <= returning:
            run = 2 * RETURN_RUN_MIN[number - 1]
            prog, anchor = RETURN_HOURS[number - 1], float(run)
            weeks.append(Week(mon, number, "return", False, prog, run, to, -1, goal, camp, None))
        else:
            buildlike = phase in ("base", "build_ski", "build_half")
            deload = buildlike and streak >= 3 and not camp
            test = None
            if deload:
                hours, run, streak = prog * DELOAD, anchor * DELOAD, 0
                for k in range(len(TESTS)):
                    t = TESTS[(tests_done + k) % len(TESTS)]
                    if t != "5 km" or since >= 3:
                        test, tests_done = t, tests_done + k + 1
                        break
            elif buildlike:
                prog = min(prog * HOURS_GROWTH, HOURS_CAP[phase])
                hours = prog * (CAMP_BOOST if camp else 1.0)
                run = min(anchor * RUN_RAMP, RUN_SHARE[phase] * (hours * 60 - STRENGTH_MIN))
                anchor, streak = run, streak + 1
            else:
                hours, run, streak = prog * PHASE_HOURS_FACTOR[phase], 0.0, 0
            weeks.append(Week(mon, number, phase, deload, round(hours, 1), round(run), to, since, goal, camp, test))
        mon, number = mon + timedelta(days=7), number + 1
    return weeks


def _round5(x: float) -> int:
    return max(int(round(x / 5.0)) * 5, 20)


def _alloc(total: float, items: list[tuple[float, float]]) -> list[int]:
    """Fordeler `total` minutter etter vekt, med tak per økt. Overskudd flyttes til de andre."""
    out = [None] * len(items)
    active = list(range(len(items)))
    left = max(total, 0.0)
    while active:
        scale = left / sum(items[i][0] for i in active)
        capped = [i for i in active if items[i][0] * scale > items[i][1]]
        if not capped:
            for i in active:
                out[i] = _round5(items[i][0] * scale)
            break
        for i in capped:
            out[i] = int(items[i][1])
            left -= items[i][1]
            active.remove(i)
        left = max(left, 0.0)
        if not active:
            break
    return out


def _strength_specs(week: Week) -> list[Spec]:
    fri = FRIDAY[(week.number - 1) % len(FRIDAY)]
    upper = Spec("Test: 5RM styrke", I_STR, "quality", 60) if week.test == "Styrke" else Spec("Styrke: Upper", I_STR, "strength", 75)
    legs_ok = (not week.deload and (week.weeks_to_race is None or week.weeks_to_race > 1)
               and not (week.phase == "build_ski" and week.weeks_to_race <= 3))
    specs = [upper]
    if legs_ok:
        specs.append(Spec("Styrke: Bein", I_STR, "legs", 60))
    specs.append(Spec(f"Styrke: {fri}", I_STR, "strength", 60))
    return specs


def week_specs(week: Week, status: dict, quality_index: int) -> list[Spec]:
    """Ukas økter uten dag. Kalenderen får bare tittelen; minutter er til planleggingen."""
    hold = bool(status.get("hold_intensity"))
    strength = _strength_specs(week)
    s_min = sum(s.minutes for s in strength)
    E = max(week.hours * 60 - s_min, 60)
    quality_ok = not week.deload and week.since_return >= 3 and not hold
    skierg_q_ok = not week.deload and week.since_return >= 2 and not hold
    R = week.run_minutes
    out = list(strength)

    if week.phase == "return":
        m = RETURN_RUN_MIN[week.number - 1]
        out += [Spec("Gå/løp", I_RUN, "run", m), Spec("Gå/løp", I_RUN, "run", m)]
        a = _alloc(E - 2 * m, [(1, 60), (1, 60)])
        out += [Spec("SkiErg", I_SKI, "aerobic", a[0]), Spec("SkiErg: rolig", I_SKI, "aerobic", a[1])]
    elif week.phase == "taper":
        out = [Spec("Styrke: Upper", I_STR, "strength", 60), Spec(f"Styrke: {FRIDAY[(week.number - 1) % 6]}", I_STR, "strength", 45)]
        if week.goal and week.goal.kind == "ski":
            out += [Spec("SkiErg", I_SKI, "aerobic", 40), Spec("SkiErg: rolig", I_SKI, "aerobic", 60),
                    Spec("SkiErg: lett", I_SKI, "aerobic", 45), Spec("Rolig løping", I_RUN, "run", 40)]
        else:
            out += [Spec("Rolig løping", I_RUN, "run", 45), (Spec("Rolig løping", I_RUN, "run", 40) if hold else Spec("Halvmaraton-fart: kort", I_RUN, "quality", 40)),
                    Spec("Rolig løping", I_RUN, "run", 30), Spec("SkiErg", I_SKI, "aerobic", 40)]
    elif week.phase == "recovery":
        out = [Spec("Styrke: Upper", I_STR, "strength", 45), Spec("Styrke: Pull", I_STR, "strength", 40),
               Spec("Rolig løping", I_RUN, "run", 40), Spec("SkiErg", I_SKI, "aerobic", 40),
               Spec("Rolig tur", I_RUN, "run", 60)]
    elif week.phase == "build_ski":
        spec = week.goal.spec_weeks
        long_ski = min(max(90 + 15 * (spec - week.weeks_to_race), 0.3 * E), 180) * (0.7 if week.deload else 1.0)  # ingen rulleski: lang økt = løping + SkiErg
        a = _alloc(max(E - R - long_ski, 40), [(0.6, 90), (0.4, 75)])
        runs = [max(round(R * 0.55), 20), max(round(R * 0.45), 20)]
        sk_q = Spec("SkiErg: intervaller", I_SKI, "quality", a[1]) if skierg_q_ok else Spec("SkiErg", I_SKI, "aerobic", a[1])
        if week.test == "SkiErg":
            sk_q = Spec("Test: SkiErg 6000 m", I_SKI, "quality", 45)
        out += [Spec(LONG_MIX, I_SKI, "long", _round5(long_ski)),
                Spec("SkiErg: rolig", I_SKI, "aerobic", a[0]), sk_q,
                Spec("Rolig løping", I_RUN, "run", runs[0]), Spec("Rolig løping", I_RUN, "run", runs[1])]
        if week.test == "5 km":
            out[-1] = Spec("Test: 5 km", I_RUN, "quality", 40)
    elif week.camp and week.phase == "base":
        long_ski = min(_round5(0.35 * E), 210)
        a = _alloc(E - long_ski - R // 2, [(1, 150), (1, 150)] + ([(0.6, 75)] if skierg_q_ok else []))
        out += [Spec("Langtur: ski", I_SKI, "long", long_ski), Spec("Ski: rolig", I_SKI, "aerobic", a[0]),
                Spec("Ski: rolig", I_SKI, "aerobic", a[1]), Spec("Rolig løping", I_RUN, "run", max(R // 2, 20))]
        if skierg_q_ok:
            out.append(Spec("Ski: intervaller", I_SKI, "quality", a[2]))
    else:  # base og build_half
        half = week.phase == "build_half"
        n_runs = 3 if R >= 150 or (half and R >= 120) else 2
        w = {2: [0.55, 0.45], 3: [0.45, 0.30, 0.25]}[n_runs]
        r = [max(round(R * x), 20) for x in w]
        cycle = ["Tempo", "Halvmaraton-fart", "Tempo"] if half else ["4x4", "Tempo", "4x4", "Bakkeintervaller"]
        q_title = cycle[quality_index % len(cycle)]
        second = Spec(q_title, I_RUN, "quality", r[1]) if quality_ok and R >= 60 else Spec("Rolig løping", I_RUN, "run", r[1])
        if week.test == "5 km":
            second = Spec("Test: 5 km", I_RUN, "quality", 40)
        if half and week.weeks_to_race == 1:
            r[0] = _round5(r[0] * 0.7)  # siste lange tur ligger en uke før løpet
        out += [Spec("Langtur", I_RUN, "long", r[0]), second]
        if n_runs == 3:
            out.append(Spec("Rolig løping", I_RUN, "run", r[2]))
        A = max(E - sum(x.minutes for x in out if x.kind in ("run", "long", "quality")), 30)
        room = 8 - len(out)
        n_sk = max(1, min(room, 1 if A < 70 else 2 if A < 190 else 3))
        a = _alloc(A, [(1, 90)] * n_sk)
        names = ["SkiErg", "SkiErg: rolig", "SkiErg: lett"]
        kinds = [(names[i], "aerobic") for i in range(n_sk)]
        if n_sk >= 2 and skierg_q_ok and week.test != "SkiErg":
            kinds[-1] = ("SkiErg: intervaller", "quality")
        if week.test == "SkiErg":
            kinds[0] = ("Test: SkiErg 6000 m", "quality")
            a[0] = 45
        out += [Spec(t, I_SKI, k, m) for (t, k), m in zip(kinds, a)]
    return out


def _penalty(days: list, specs: list[Spec], carry: bool, blocked: frozenset = frozenset()) -> int:
    p = 0
    p += 2000 * sum(1 for d in days if d in blocked)  # konkurransedagen er ikke en treningsdag
    by_day: dict[int, list[int]] = {}
    for i, d in enumerate(days):
        if d is not None:
            by_day.setdefault(d, []).append(i)
    for idx in by_day.values():
        if len(idx) > 2:
            p += 1000
        elif len(idx) == 2:
            a, b = specs[idx[0]], specs[idx[1]]
            p += 6
            if a.title == b.title:
                p += 500
            if a.kind in ("strength", "legs") and b.kind in ("strength", "legs"):
                p += 15
            hards = a.hard + b.hard
            if hards == 2:
                p += 80
            elif hards == 1:
                other = b if a.hard else a
                p += 30 if other.kind in CARDIO else 10
    if all(d is not None for d in days):
        empty = [d for d in range(7) if d not in by_day]
        if not empty:
            p += 200
        else:
            longs = [days[i] for i, s in enumerate(specs) if s.kind == "long"]
            if longs and not any(abs(e - ld) == 1 for e in empty for ld in longs):
                p += 8
    for i, s in enumerate(specs):
        if days[i] is None:
            continue
        if s.kind == "long" and days[i] not in (5, 6):
            p += 12
        if s.hard and days[i] == 0 and carry:
            p += 30
        for j, t in enumerate(specs):
            if days[j] is not None and days[j] == days[i] + 1 and s.hard and t.hard:
                p += PAIR.get((s.kind, t.kind), 25)
    return p


def schedule(specs: list[Spec], carry: bool = False, blocked: frozenset = frozenset()) -> list[int]:
    """Velger dag (0 = mandag) for hver økt. Samme input gir alltid samme svar."""
    order = sorted(range(len(specs)), key=lambda i: (
        {"long": 0, "quality": 1, "legs": 2}.get(specs[i].kind, 3), -specs[i].minutes, i))
    days: list = [None] * len(specs)
    for i in order:
        best = min(range(7), key=lambda d: (_penalty(days[:i] + [d] + days[i + 1:], specs, carry, blocked), d))
        days[i] = best
    score = _penalty(days, specs, carry, blocked)
    for _ in range(40):
        improved = False
        for i in range(len(specs)):
            for d in range(7):
                trial = days[:i] + [d] + days[i + 1:]
                s = _penalty(trial, specs, carry, blocked)
                if s < score:
                    days, score, improved = trial, s, True
        for i in range(len(specs)):
            for j in range(i + 1, len(specs)):
                trial = list(days)
                trial[i], trial[j] = trial[j], trial[i]
                s = _penalty(trial, specs, carry, blocked)
                if s < score:
                    days, score, improved = trial, s, True
        if not improved:
            break
    return days


def _on_snow(s: Session) -> Session:
    t = s.title
    if t in ("Langtur", LONG_MIX):
        return replace(s, title="Langtur: ski", icon=I_SKI)
    if t in QUALITY_RUN or t == "SkiErg: intervaller":
        return replace(s, title="Ski: intervaller", icon=I_SKI)
    if t in ("SkiErg", "SkiErg: rolig", "SkiErg: lett"):
        return replace(s, title="Ski: rolig", icon=I_SKI, kind="aerobic")
    return s


def plan_weeks(today: date, data: dict) -> list[tuple[Week, list[Session]]]:
    """Ukene i vinduet (standard 13 uker fra denne uka) med økter plassert på dager."""
    status = data["status"]
    goals = goals_from(data.get("goals", []))
    windows = windows_from(data.get("availability", []))
    plan_start = date.fromisoformat(status["plan_start"])
    first = max(monday(today), monday(plan_start))
    last = first + timedelta(days=7 * (int(data.get("horizon_weeks", 13)) - 1))
    out, quality_index, carry = [], 0, False
    for week in build_weeks(plan_start, last, goals, status, windows):
        specs = week_specs(week, status, quality_index)
        quality_index += sum(1 for s in specs if s.title in QUALITY_RUN)
        blocked = frozenset({week.goal.day.weekday()}) if week.phase == "taper" and week.goal else frozenset()
        days = schedule(specs, carry, blocked)
        carry = any(s.hard and d == 6 for s, d in zip(specs, days))
        sessions = []
        for s, d in sorted(zip(specs, days), key=lambda x: (x[1], x[0].kind != "strength", x[0].title)):
            day = week.monday + timedelta(days=d)
            item = Session(day, s.title, s.icon, s.kind, s.minutes)
            if any(w.start <= day <= w.end and "ski" in w.modes for w in windows):
                item = _on_snow(item)
            if day >= plan_start:
                sessions.append(item)
        if week.monday >= first:
            out.append((week, sessions))
    return out


def generate(today: date, data: dict) -> list[Session]:
    return [s for _w, sessions in plan_weeks(today, data) for s in sessions]


def describe(today: date, data: dict) -> str:
    """Oversikt til planlegging her (skrives ut med `python3 build.py --plan`)."""
    from .fmt import nb_span
    names = "man tir ons tor fre lør søn".split()
    lines = []
    for g in goals_from(data.get("goals", [])):
        lines.append(f"Mål: {g.name}, {g.day:%d.%m.%Y}" + (f", {g.target}" if g.target else ""))
    for week, sessions in plan_weeks(today, data):
        total = sum(s.minutes for s in sessions)
        flags = ", ".join(x for x in [PHASE_NAME[week.phase], "lett uke" if week.deload else "", "skileir" if week.camp else "",
                                      f"test: {week.test}" if week.test else ""] if x)
        lines.append("")
        lines.append(f"Uke {week.number}  {nb_span(week.monday, week.monday + timedelta(days=6))}  {flags}")
        lines.append(f"  {len(sessions)} økter, {total // 60} t {total % 60:02d} min (mål {week.hours:.1f} t), løping ca. {week.run_minutes} min")
        for s in sessions:
            lines.append(f"  {names[s.day.weekday()]} {s.day:%d.%m}  {s.icon} {s.title}  ({s.minutes} min)")
    return "\n".join(lines)
