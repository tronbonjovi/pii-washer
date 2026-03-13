"""PII Shield — Component 3: Placeholder Generator.

Takes a list of PII detections (from Component 2) and assigns
category-prefixed placeholders, consolidating duplicate values
into single entries.
"""

import copy


class PlaceholderGenerator:
    """Assigns placeholder labels to PII detections and consolidates duplicates."""

    CATEGORY_PREFIX_MAP = {
        "NAME": "Person",
        "ADDRESS": "Address",
        "PHONE": "Phone",
        "EMAIL": "Email",
        "SSN": "SSN",
        "DOB": "DOB",
        "CCN": "CCN",
        "IP": "IP",
        "URL": "URL",
    }

    VALID_CATEGORIES = list(CATEGORY_PREFIX_MAP.keys())

    def assign_placeholders(self, detections: list[dict]) -> list[dict]:
        """Take a list of PII detections and return a consolidated list with placeholders assigned.

        Parameters:
            detections: A list of detection dicts in Component 2's output format.

        Returns:
            A new list of detection dicts with duplicates consolidated,
            placeholders assigned, and IDs reassigned sequentially.
        """
        if not isinstance(detections, list):
            raise TypeError("Expected a list of detections")

        if len(detections) == 0:
            raise ValueError("Detections list cannot be empty")

        required_fields = ("id", "category", "original_value", "positions", "confidence")
        for det in detections:
            for field in required_fields:
                if field not in det:
                    raise ValueError(f"Detection missing required field: {field}")
            if det["category"] not in self.VALID_CATEGORIES:
                raise ValueError(f"Unknown category: {det['category']}")

        # Deep copy to avoid mutating input
        dets = copy.deepcopy(detections)

        # Group by (category, lowercase original_value)
        groups: dict[tuple[str, str], list[dict]] = {}
        for det in dets:
            key = (det["category"], det["original_value"].lower())
            if key not in groups:
                groups[key] = []
            groups[key].append(det)

        # Build consolidated entries
        consolidated = []
        for group_dets in groups.values():
            # Sort detections in group by earliest start position
            group_dets.sort(key=lambda d: d["positions"][0]["start"])

            # Merge all positions, sorted by start
            all_positions = []
            for d in group_dets:
                all_positions.extend(d["positions"])
            all_positions.sort(key=lambda p: p["start"])

            # First occurrence determines canonical value
            canonical = group_dets[0]

            # Highest confidence
            max_confidence = max(d["confidence"] for d in group_dets)

            consolidated.append({
                "category": canonical["category"],
                "original_value": canonical["original_value"],
                "positions": all_positions,
                "confidence": max_confidence,
                "earliest_start": all_positions[0]["start"],
            })

        # Sort by first occurrence position
        consolidated.sort(key=lambda entry: entry["earliest_start"])

        # Assign per-category placeholders based on encounter order
        category_counters: dict[str, int] = {}
        for entry in consolidated:
            cat = entry["category"]
            category_counters[cat] = category_counters.get(cat, 0) + 1
            entry["placeholder"] = self.generate_placeholder(cat, category_counters[cat])

        # Reassign IDs and clean up
        result = []
        for i, entry in enumerate(consolidated, start=1):
            result.append({
                "id": f"pii_{i:03d}",
                "category": entry["category"],
                "original_value": entry["original_value"],
                "placeholder": entry["placeholder"],
                "positions": entry["positions"],
                "confidence": entry["confidence"],
            })

        return result

    def generate_placeholder(self, category: str, counter: int) -> str:
        """Generate a single placeholder string for a given category and counter.

        Parameters:
            category: A valid PII Shield category string.
            counter: A positive integer (1-based).

        Returns:
            The placeholder string, e.g. "[Person_1]".
        """
        if category not in self.CATEGORY_PREFIX_MAP:
            raise ValueError(f"Unknown category: {category}")

        if not isinstance(counter, int) or isinstance(counter, bool) or counter < 1:
            raise ValueError("Counter must be a positive integer")

        prefix = self.CATEGORY_PREFIX_MAP[category]
        return f"[{prefix}_{counter}]"

    def get_category_prefix_map(self) -> dict:
        """Return the category-to-placeholder-prefix mapping."""
        return dict(self.CATEGORY_PREFIX_MAP)
