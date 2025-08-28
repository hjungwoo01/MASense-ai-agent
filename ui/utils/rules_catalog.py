from typing import Dict, List, Optional, Tuple
import json, os

RULESET_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "mas_ruleset.json")

def load_rules() -> Dict:
    with open(RULESET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def sectors(rules: Dict) -> List[str]:
    return [rules[k]["sector"] for k in rules.keys()]

def activities_for_sector(rules: Dict, sector_name: str) -> List[str]:
    for key, block in rules.items():
        if block["sector"] == sector_name:
            return [c["activity"] for c in block.get("criteria", [])]
    return []

def find_activity_info(rules: Dict, sector_name: str, activity: str) -> Optional[Dict]:
    for _, block in rules.items():
        if block["sector"] != sector_name:
            continue
        for c in block.get("criteria", []):
            if c["activity"] == activity:
                return {
                    "objectives": block.get("objectives", []),
                    "classification": c.get("classification"),
                    "description": c.get("description"),
                    "examples": c.get("examples", []),
                    "suggestion": c.get("suggestion"),
                    "source": c.get("source"),
                }
    return None