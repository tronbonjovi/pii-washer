"""PII Shield — Component 4: Text Substitution Engine.

Performs bidirectional text replacement:
- Depersonalize: PII → placeholder (position-based, right-to-left)
- Repersonalize: placeholder → PII (string-based, longest-first)
"""

import re


class TextSubstitutionEngine:
    """Performs bidirectional text substitution between PII values and placeholders."""

    PLACEHOLDER_PATTERN = r"\[(?:Person|Address|Phone|Email|SSN|DOB|CCN|IP|URL)_\d+\]"

    VALID_DIRECTIONS = ["depersonalize", "repersonalize"]

    def depersonalize(self, text: str, detections: list[dict]) -> str:
        """Replace PII in the original text with placeholders using position-based replacement.

        Parameters:
            text: The original text string to depersonalize.
            detections: A list of detection dicts with original_value, placeholder, and positions.

        Returns:
            The depersonalized text with confirmed PII replaced by placeholders.
        """
        if not isinstance(text, str) or text == "":
            raise ValueError("Text cannot be empty")
        if not isinstance(detections, list):
            raise TypeError("Expected a list of detections")
        if len(detections) == 0:
            return text

        for det in detections:
            for field in ("original_value", "placeholder", "positions"):
                if field not in det:
                    raise ValueError(f"Detection missing required field: {field}")

        filtered = [
            det for det in detections
            if "status" not in det or det["status"] == "confirmed"
        ]

        if not filtered:
            return text

        # Collect all (start, end, placeholder) tuples
        positions = []
        for det in filtered:
            for pos in det["positions"]:
                positions.append((pos["start"], pos["end"], det["placeholder"]))

        # Sort by start descending (right-to-left)
        positions.sort(key=lambda p: p[0], reverse=True)

        # Process replacements, tracking replaced spans for overlap detection
        replaced_spans = []
        result = text
        for start, end, placeholder in positions:
            # Check overlap with already-replaced spans
            overlaps = False
            for rs, re_ in replaced_spans:
                if start < re_ and end > rs:
                    overlaps = True
                    break
            if overlaps:
                continue

            result = result[:start] + placeholder + result[end:]
            replaced_spans.append((start, end))

        return result

    def repersonalize(self, text: str, detections: list[dict]) -> dict:
        """Replace placeholders in response text with original PII values.

        Parameters:
            text: The response text containing placeholders.
            detections: A list of detection dicts with original_value and placeholder.

        Returns:
            A dict with text, matched, unmatched_from_map, unknown_in_text, and match_summary.
        """
        if not isinstance(text, str) or text == "":
            raise ValueError("Text cannot be empty")
        if not isinstance(detections, list):
            raise TypeError("Expected a list of detections")

        if len(detections) == 0:
            unknown = re.findall(self.PLACEHOLDER_PATTERN, text)
            return {
                "text": text,
                "matched": [],
                "unmatched_from_map": [],
                "unknown_in_text": unknown,
                "match_summary": "No placeholders to match",
            }

        for det in detections:
            for field in ("original_value", "placeholder"):
                if field not in det:
                    raise ValueError(f"Detection missing required field: {field}")

        replacement_map = self.build_replacement_map(detections, "repersonalize")

        if not replacement_map:
            unknown = re.findall(self.PLACEHOLDER_PATTERN, text)
            return {
                "text": text,
                "matched": [],
                "unmatched_from_map": [],
                "unknown_in_text": unknown,
                "match_summary": "No placeholders to match",
            }

        # Sort by placeholder length descending (longest first)
        sorted_placeholders = sorted(replacement_map.keys(), key=len, reverse=True)

        matched = []
        unmatched_from_map = []
        result = text

        for placeholder in sorted_placeholders:
            if placeholder in result:
                result = result.replace(placeholder, replacement_map[placeholder])
                matched.append(placeholder)
            else:
                unmatched_from_map.append(placeholder)

        # Scan for unknown placeholders remaining in the text
        unknown_in_text = [
            m for m in re.findall(self.PLACEHOLDER_PATTERN, result)
            if m not in replacement_map
        ]

        total = len(replacement_map)
        matched_count = len(matched)

        if total == 0:
            match_summary = "No placeholders to match"
        elif matched_count == total:
            match_summary = f"{matched_count}/{total} placeholders matched and restored"
        else:
            unmatched_count = total - matched_count
            unmatched_names = ", ".join(unmatched_from_map)
            match_summary = (
                f"{matched_count}/{total} placeholders matched — "
                f"{unmatched_count} unmatched: {unmatched_names}"
            )

        return {
            "text": result,
            "matched": matched,
            "unmatched_from_map": unmatched_from_map,
            "unknown_in_text": unknown_in_text,
            "match_summary": match_summary,
        }

    def build_replacement_map(self, detections: list[dict], direction: str = "depersonalize") -> dict:
        """Build a mapping dictionary from the detection list.

        Parameters:
            detections: A list of detection dicts.
            direction: Either "depersonalize" or "repersonalize".

        Returns:
            A dict mapping original_value→placeholder or placeholder→original_value.
        """
        if direction not in self.VALID_DIRECTIONS:
            raise ValueError(
                f"Invalid direction: {direction}. Must be 'depersonalize' or 'repersonalize'"
            )

        filtered = [
            det for det in detections
            if "status" not in det or det["status"] == "confirmed"
        ]

        if direction == "depersonalize":
            return {det["original_value"]: det["placeholder"] for det in filtered}
        else:
            return {det["placeholder"]: det["original_value"] for det in filtered}
