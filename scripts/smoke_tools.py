#!/usr/bin/env python
"""Friday F4 smoke — hit each analytical tool through the DataGateway and print
its shape + latency. Confirms the seam works end-to-end against the seeded DB.

    DROOMZAAK_POSTGRES_URL=postgresql://… uv run python scripts/smoke_tools.py
"""

from __future__ import annotations

import asyncio

from backend.app import droomzaak_tools
from backend.app.agent_loop import AgentRun
from backend.app.data_gateway import gateway

LISA = {"sector": "horeca", "sector_group": "horeca", "nace_code": "56.101",
        "scale": "small", "seats_guess": 18, "budget_eur_guess": 60000}


async def main():
    await gateway.connect()
    run = AgentRun()
    checks = [
        ("peer_benchmarks_statbel", {"nace_code": "56.101", "refnis": "44021"}),
        ("score_locations", {"dream_profile": LISA, "top_n": 3}),
        ("rent_benchmark", {"sector_id": "44021A23B"}),
        ("permit_checklist_for", {"nace_code": "56.101",
                                  "attributes": {"serves_alcohol": "gegiste", "seating": "terrace"}}),
        ("subsidies_for", {"dream_profile": LISA}),
        ("legal_form_advisor", {"dream_profile": LISA, "chosen_location": {"address": "Vrijdagmarkt 12"}}),
    ]
    for name, args in checks:
        result = await droomzaak_tools.HANDLERS[name](args, run)
        ok = "error" not in result
        print(f"{'OK ' if ok else 'ERR'} {name}: keys={list(result)[:4]}")
        if not ok:
            print(f"    {result}")
    print("\nDataGateway audit (analytical reads this run):")
    for entry in gateway.drain_audit():
        print(f"  - {entry['tool_name']}: {entry['rows_returned']} rows in {entry['latency_ms']}ms")
    await gateway.close()


if __name__ == "__main__":
    asyncio.run(main())
