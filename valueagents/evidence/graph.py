# ./valueagents/evidence/graph.py
"""EvidenceGraph — Phase 1 F1.2

Append-only 证据图，4 种 view。
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from .schema import EvidenceBundle


ViewName = Literal["full", "claims", "signals", "compact"]


class EvidenceGraph:
    def __init__(self, ticker: str, end_date: str):
        self.ticker = ticker
        self.end_date = end_date
        self._evidence: dict[str, dict[str, Any]] = {}
        self._claims: dict[str, dict[str, Any]] = {}
        self._signals: dict[str, list[dict[str, Any]]] = {}
        self._narratives: dict[str, str] = {}

    def add_bundle(self, bundle: EvidenceBundle) -> None:
        if bundle.ticker != self.ticker:
            raise ValueError(
                f"Bundle ticker mismatch: {bundle.ticker!r} != {self.ticker!r}"
            )
        for ev in bundle.evidence:
            self._evidence[ev.id] = ev.model_dump()
        for cl in bundle.claims:
            self._claims[cl.id] = cl.model_dump()
        self._signals[bundle.agent_id] = [s.model_dump() for s in bundle.signals]
        self._narratives[bundle.agent_id] = bundle.narrative

    def get_evidence(self, ev_id: str) -> Optional[dict[str, Any]]:
        return self._evidence.get(ev_id)

    def get_claim(self, cl_id: str) -> Optional[dict[str, Any]]:
        return self._claims.get(cl_id)

    def all_signals(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for sigs in self._signals.values():
            out.extend(sigs)
        return out

    def keys(self) -> dict[str, int]:
        return {
            "evidence": len(self._evidence),
            "claims": len(self._claims),
            "agents": len(self._signals),
            "signals": sum(len(v) for v in self._signals.values()),
        }

    def to_view(
        self,
        view: ViewName,
        filter: Optional[dict[str, Any]] = None,
        max_chars: int = 3000,
    ) -> str:
        # 1. 先校验 view 参数（无论图是否为空，非法 view 都 raise）
        if view not in ("full", "claims", "signals", "compact"):
            raise ValueError(f"Unknown view: {view!r}")

        # 2. 空图：直接返回标记（不进入渲染逻辑）
        if not self._evidence and not self._claims and not self._signals:
            return "(empty evidence graph)"

        # 3. 渲染
        if view == "full":
            text = self._render_full(filter)
        elif view == "claims":
            text = self._render_claims(filter)
        elif view == "signals":
            text = self._render_signals(filter)
        else:  # compact
            text = self._render_compact(filter)

        if not text:
            return "(empty evidence graph)"
        if len(text) > max_chars:
            text = text[: max_chars - 3] + "..."
        return text
        
    def _render_full(self, filter):
        claims = self._filtered_claims(filter)
        signals = self._filtered_signals(filter)
        ev_ids = {eid for cl in claims for eid in cl["evidence_ids"]}
        lines = [
            f"# Evidence Graph — {self.ticker} @ {self.end_date}",
            f"# counts: {self.keys()}",
            "",
            "## Evidence",
        ]
        if ev_ids:
            for eid in sorted(ev_ids):
                ev = self._evidence.get(eid)
                if not ev:
                    continue
                lines.append(
                    f"- `{eid}` ({ev['source']}/{ev['source_type']}) "
                    f"ref={ev['raw_ref']}"
                )
                lines.append(f"  content: {str(ev['content'])[:200]}")
        else:
            lines.append("(no evidence matched)")
        lines += ["", "## Claims"]
        if claims:
            for cl in claims:
                lines.append(
                    f"- `{cl['id']}` [{cl['framework']}] conf={cl['confidence']:.2f}"
                )
                lines.append(f"  statement: {cl['statement']}")
                lines.append(f"  evidence: {cl['evidence_ids']}")
                if cl.get("counter_claim_ids"):
                    lines.append(f"  counters: {cl['counter_claim_ids']}")
        else:
            lines.append("(no claims matched)")
        lines += ["", "## Signals"]
        if signals:
            for sig in signals:
                fw = sig.get("framework") or "-"
                lines.append(
                    f"- {sig['ticker']} [{sig['dimension']} / {fw}] "
                    f"{sig['direction']} (strength={sig['strength']:.2f})"
                )
                lines.append(f"  claims: {sig['claim_ids']}")
                lines.append(f"  provenance: {sig['provenance']}")
        else:
            lines.append("(no signals matched)")
        return "\n".join(lines)

    def _render_claims(self, filter):
        claims = self._filtered_claims(filter)
        if not claims:
            return "(no claims matched)"
        lines = [f"# Claims — {self.ticker} @ {self.end_date}"]
        for cl in claims:
            lines.append(
                f"- `{cl['id']}` [{cl['framework']}] conf={cl['confidence']:.2f} "
                f"← evidence={cl['evidence_ids']}"
            )
            stmt = cl["statement"].replace("\n", " ")
            if len(stmt) > 200:
                stmt = stmt[:197] + "..."
            lines.append(f"  {stmt}")
        return "\n".join(lines)

    def _render_signals(self, filter):
        signals = self._filtered_signals(filter)
        if not signals:
            return "(no signals matched)"
        lines = [f"# Signals — {self.ticker} @ {self.end_date}"]
        for sig in sorted(signals, key=lambda s: (s["dimension"], s.get("framework") or "", s["direction"])):
            fw = sig.get("framework") or "-"
            lines.append(
                f"- [{sig['dimension']} / {fw}] {sig['direction']} "
                f"(strength={sig['strength']:.2f}, claims={len(sig['claim_ids'])})"
            )
        return "\n".join(lines)

    def _render_compact(self, filter):
        signals = self._filtered_signals(filter)
        if not signals:
            return "(no signals matched)"
        groups: dict[str, list[dict[str, Any]]] = {}
        for sig in signals:
            key = sig.get("framework") or f"dim:{sig['dimension']}"
            groups.setdefault(key, []).append(sig)
        lines = [f"# Compact — {self.ticker} @ {self.end_date}"]
        for key in sorted(groups.keys()):
            sigs = groups[key]
            counts: dict[str, int] = {"bullish": 0, "bearish": 0, "neutral": 0}
            avg = 0.0
            for s in sigs:
                counts[s["direction"]] = counts.get(s["direction"], 0) + 1
                avg += s["strength"]
            avg /= len(sigs) if sigs else 1
            dominant = max(counts, key=counts.get) if counts else "neutral"
            lines.append(
                f"- {key}: {dominant} "
                f"(n={len(sigs)}, avg_strength={avg:.2f}, "
                f"b/b/n={counts['bullish']}/{counts['bearish']}/{counts['neutral']})"
            )
        return "\n".join(lines)

    def _filtered_claims(self, filter):
        claims = list(self._claims.values())
        if not filter:
            return claims
        fw = filter.get("framework")
        if fw:
            claims = [c for c in claims if c["framework"] == fw]
        min_conf = filter.get("min_confidence")
        if min_conf is not None:
            claims = [c for c in claims if c["confidence"] >= float(min_conf)]
        return claims

    def _filtered_signals(self, filter):
        signals = self.all_signals()
        if not filter:
            return signals
        fw = filter.get("framework")
        if fw:
            signals = [s for s in signals if s.get("framework") == fw]
        dim = filter.get("dimension")
        if dim:
            signals = [s for s in signals if s["dimension"] == dim]
        agent = filter.get("agent_id")
        if agent and agent in self._signals:
            signals = [s for s in signals if s in self._signals[agent]]
        return signals

    def to_dict(self):
        return {
            "ticker": self.ticker,
            "end_date": self.end_date,
            "evidence": list(self._evidence.values()),
            "claims": list(self._claims.values()),
            "signals_by_agent": {k: list(v) for k, v in self._signals.items()},
            "narratives": dict(self._narratives),
        }

    @classmethod
    def from_dict(cls, data):
        g = cls(data["ticker"], data["end_date"])
        g._evidence = {ev["id"]: ev for ev in data.get("evidence", [])}
        g._claims = {cl["id"]: cl for cl in data.get("claims", [])}
        g._signals = {k: list(v) for k, v in (data.get("signals_by_agent") or {}).items()}
        g._narratives = dict(data.get("narratives") or {})
        return g
