"""H4 execution selection; independent of the frozen H3 agent and job server.

The caller owns execution, persistence, and the worker process. Only aggregate
profile and pilot data are sent to Solar. Memory limits here are model estimates.
"""
import json
from time import perf_counter

from src import agent
from src.mining_job import SETTINGS

TOOLS = [
    {"type": "function", "function": {"name": "pilot", "description": "Run one fixed-size sample trial. Sample counts are not full-data results.",
      "parameters": {"type": "object", "properties": {"setting": {"type": "string", "enum": list(SETTINGS)}}, "required": ["setting"]}}},
    {"type": "function", "function": {"name": "choose", "description": "Choose one setting for exact mining.",
      "parameters": {"type": "object", "properties": {"setting": {"type": "string", "enum": list(SETTINGS)},
      "reason": {"type": "string"}}, "required": ["setting", "reason"]}}},
]


def valid_settings(job, excluded=()):
    available = []
    for setting in SETTINGS:
        if setting in excluded:
            continue
        try:
            job.validate_setting(setting)
            available.append(setting)
        except ValueError:
            pass
    return available


def baseline(job, excluded=()):
    """Provisional deterministic baseline: first feasible setting in fixed order."""
    choices = valid_settings(job, excluded)
    if not choices:
        raise ValueError("No setting fits the modeled memory budget")
    return choices[0]


class MiningSelector:
    """Per-job state. Call select(), then reselect(failed_setting, reason) at most once."""

    def __init__(self, job, strategy="solar_pilot", chat=None, emit=None):
        if strategy not in ("rules", "solar_once", "solar_pilot"):
            raise ValueError("unknown selection strategy")
        self.job, self.strategy = job, strategy
        self.chat = chat or agent.chat
        self.emit = emit
        self.history = []
        self.pilot_used = False
        self.reselection_used = False

    def _event(self, kind, **fields):
        event = {"event": kind, **fields}
        self.history.append(event)
        if self.emit:
            self.emit(event)

    def select(self):
        return self._select(())

    def reselect(self, failed_setting, reason):
        if self.reselection_used or self.strategy != "solar_pilot":
            raise ValueError("Reselection is not available")
        if failed_setting not in SETTINGS:
            raise ValueError("unknown failed setting")
        self.reselection_used = True
        self._event("reselection", failed_setting=failed_setting, reason=str(reason)[:300])
        return self._select((failed_setting,))

    def _select(self, excluded):
        feasible = valid_settings(self.job, excluded)
        if not feasible:
            self._event("failed", reason="No setting fits the modeled memory budget")
            raise ValueError("No setting fits the modeled memory budget")
        profile = self.job.profile()
        self._event("profile", profile=profile)
        if self.strategy == "rules":
            selected = baseline(self.job, excluded)
            self._event("selected", setting=selected, source="rules")
            return selected
        messages = [{"role": "system", "content": "Choose an exact mining setting from the profile and memory budget. "
                     "Memory is a modeled estimate, not peak process memory. You may request at most one sample pilot; "
                     "sample results are not full-data results. Use choose to submit your selection."},
                    {"role": "user", "content": json.dumps({"profile": profile, "feasible": feasible,
                     "excluded": list(excluded), "pilot_already_used": self.pilot_used})}]
        started = perf_counter()
        try:
            for _ in range(1 if self.strategy == "solar_once" else 4):
                specs = TOOLS if self.strategy == "solar_pilot" and not self.pilot_used else [TOOLS[1]]
                msg = self.chat(messages, specs)
                calls = msg.get("tool_calls") or []
                if not calls:
                    raise ValueError("Solar returned no selection")
                messages.append(msg)
                chosen = None
                for call in calls:
                    name = call.get("function", {}).get("name")
                    try:
                        args = json.loads(call["function"].get("arguments") or "{}")
                        setting = args["setting"]
                        if setting not in feasible:
                            raise ValueError("Setting is unavailable or exceeds the modeled memory budget")
                        if name == "pilot":
                            if self.strategy != "solar_pilot" or self.pilot_used:
                                raise ValueError("Pilot is not available")
                            self.pilot_used = True
                            result = self.job.pilot(setting)
                            self._event("pilot", result=result, scope="sample")
                            output = {"scope": "sample only", **result}
                        elif name == "choose":
                            chosen = setting
                            output = {"accepted": True}
                            self._event("solar_choice", setting=setting, reason=str(args.get("reason", ""))[:500])
                        else:
                            raise ValueError("Unknown tool")
                    except (KeyError, TypeError, ValueError) as e:
                        output = {"error": str(e)}
                        self._event("invalid_tool_call", tool=name, reason=str(e))
                    messages.append({"role": "tool", "tool_call_id": call.get("id"), "content": json.dumps(output)})
                if chosen is not None:
                    self._event("selected", setting=chosen, source="solar", selection_seconds=perf_counter()-started)
                    return chosen
            raise ValueError("Solar did not produce a valid selection")
        except (Exception, SystemExit) as e:
            selected = baseline(self.job, excluded)
            self._event("fallback", reason=str(e)[:300], setting=selected, selection_seconds=perf_counter()-started)
            self._event("selected", setting=selected, source="rules_fallback")
            return selected
