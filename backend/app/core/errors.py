"""Domain errors with bilingual (English / Persian) messages.

Every error surfaced by the API carries a stable machine code plus a human
readable message in both languages, so the Android client never has to build
sentences of its own.
"""

from __future__ import annotations

from typing import Any

MESSAGES: dict[str, tuple[str, str]] = {
    "out_of_if97_range": (
        "The requested pressure/temperature lies outside the IAPWS-IF97 validity range.",
        "\u0645\u0642\u062f\u0627\u0631 \u0641\u0634\u0627\u0631 \u06cc\u0627 \u062f\u0645\u0627 \u062e\u0627\u0631\u062c \u0627\u0632 \u0645\u062d\u062f\u0648\u062f\u0647\u0654 \u0645\u0639\u062a\u0628\u0631 IAPWS-IF97 \u0627\u0633\u062a.",
    ),
    "out_of_envelope": (
        "Input outside the allowed range.",
        "\u0648\u0631\u0648\u062f\u06cc \u062e\u0627\u0631\u062c \u0627\u0632 \u0645\u062d\u062f\u0648\u062f\u0647\u0654 \u0645\u062c\u0627\u0632 \u0627\u0633\u062a.",
    ),
    "invalid_flow": (
        "Mass flow must be greater than zero.",
        "\u062f\u0628\u06cc \u062c\u0631\u0645\u06cc \u0628\u0627\u06cc\u062f \u0628\u0632\u0631\u06af\u200c\u062a\u0631 \u0627\u0632 \u0635\u0641\u0631 \u0628\u0627\u0634\u062f.",
    ),
    "negative_spray": (
        "Spray flow cannot be negative.",
        "\u062f\u0628\u06cc \u067e\u0627\u0634\u0634 \u0646\u0645\u06cc\u200c\u062a\u0648\u0627\u0646\u062f \u0645\u0646\u0641\u06cc \u0628\u0627\u0634\u062f.",
    ),
    "invalid_geometry": (
        "Geometry is not valid for a heat transfer calculation.",
        "\u0647\u0646\u062f\u0633\u0647\u0654 \u0648\u0627\u0631\u062f \u0634\u062f\u0647 \u0628\u0631\u0627\u06cc \u0645\u062d\u0627\u0633\u0628\u0647\u0654 \u0627\u0646\u062a\u0642\u0627\u0644 \u062d\u0631\u0627\u0631\u062a \u0645\u0639\u062a\u0628\u0631 \u0646\u06cc\u0633\u062a.",
    ),
    "invalid_dt": (
        "Time step must be positive and shorter than the requested duration.",
        "\u06af\u0627\u0645 \u0632\u0645\u0627\u0646\u06cc \u0628\u0627\u06cc\u062f \u0645\u062b\u0628\u062a \u0648 \u06a9\u0648\u0686\u06a9\u200c\u062a\u0631 \u0627\u0632 \u0645\u062f\u062a \u0634\u0628\u06cc\u0647\u200c\u0633\u0627\u0632\u06cc \u0628\u0627\u0634\u062f.",
    ),
    "initial_state_inconsistent": (
        "Initial state is not physically consistent: metal must be hotter than steam and heat input must be non-negative.",
        "\u0634\u0631\u0627\u06cc\u0637 \u0627\u0628\u062a\u062f\u0627\u06cc\u06cc \u0641\u06cc\u0632\u06cc\u06a9\u06cc \u0646\u06cc\u0633\u062a: \u062f\u0645\u0627\u06cc \u0641\u0644\u0632 \u0628\u0627\u06cc\u062f \u0628\u06cc\u0634\u200c\u062a\u0631 \u0627\u0632 \u0628\u062e\u0627\u0631 \u0648 \u062d\u0631\u0627\u0631\u062a \u0648\u0631\u0648\u062f\u06cc \u0646\u0627\u0645\u0646\u0641\u06cc \u0628\u0627\u0634\u062f.",
    ),
    "previous_run_not_found": (
        "The referenced previous run does not exist.",
        "\u0634\u0628\u06cc\u0647\u200c\u0633\u0627\u0632\u06cc \u0642\u0628\u0644\u06cc \u0627\u0631\u062c\u0627\u0639\u200c\u062f\u0627\u062f\u0647\u200c\u0634\u062f\u0647 \u0648\u062c\u0648\u062f \u0646\u062f\u0627\u0631\u062f.",
    ),
    "unknown_htc_method": (
        "Unknown heat transfer coefficient method.",
        "\u0631\u0648\u0634 \u0645\u062d\u0627\u0633\u0628\u0647\u0654 \u0636\u0631\u06cc\u0628 \u0627\u0646\u062a\u0642\u0627\u0644 \u062d\u0631\u0627\u0631\u062a \u0646\u0627\u0634\u0646\u0627\u062e\u062a\u0647 \u0627\u0633\u062a.",
    ),
    "unknown_burner": (
        "Unknown burner tag.",
        "\u062a\u06af \u0634\u0631\u0639\u200c\u06a9\u0646 \u0646\u0627\u0634\u0646\u0627\u062e\u062a\u0647 \u0627\u0633\u062a.",
    ),
    "n_nodes_unsupported": (
        "Only the single-node (N = 1) platen model is enabled in this version.",
        "\u062f\u0631 \u0627\u06cc\u0646 \u0646\u0633\u062e\u0647 \u062a\u0646\u0647\u0627 \u0645\u062f\u0644 \u062a\u06a9\u200c\u06af\u0631\u0647\u200c\u0627\u06cc (N = 1) \u0641\u0639\u0627\u0644 \u0627\u0633\u062a.",
    ),
    "no_calibration_data": (
        "At least one historical operating point is required.",
        "\u062d\u062f\u0627\u0642\u0644 \u06cc\u06a9 \u0646\u0642\u0637\u0647\u0654 \u0628\u0647\u0631\u0647\u200c\u0628\u0631\u062f\u0627\u0631\u06cc \u062a\u0627\u0631\u06cc\u062e\u06cc \u0644\u0627\u0632\u0645 \u0627\u0633\u062a.",
    ),
    "rate_limited": (
        "Too many requests. Please retry shortly.",
        "\u062a\u0639\u062f\u0627\u062f \u062f\u0631\u062e\u0648\u0627\u0633\u062a\u200c\u0647\u0627 \u0632\u06cc\u0627\u062f \u0627\u0633\u062a\u061b \u0644\u0637\u0641\u0627\u064b \u06a9\u0645\u06cc \u0628\u0639\u062f \u062f\u0648\u0628\u0627\u0631\u0647 \u062a\u0644\u0627\u0634 \u06a9\u0646\u06cc\u062f.",
    ),
}


class DomainError(Exception):
    """A business-rule failure that maps onto an HTTP error response."""

    status_code = 422

    def __init__(
        self,
        code: str,
        message_en: str | None = None,
        message_fa: str | None = None,
        status_code: int = 422,
        context: dict[str, Any] | None = None,
    ) -> None:
        default_en, default_fa = MESSAGES.get(code, (code, code))
        self.code = code
        self.message_en = message_en or default_en
        self.message_fa = message_fa or default_fa
        self.status_code = status_code
        self.context = context or {}
        super().__init__(f"{code}: {self.message_en}")

    def to_payload(self) -> dict[str, Any]:
        """Serialise the error for the API and for structured logging."""
        return {
            "code": self.code,
            "message_en": self.message_en,
            "message_fa": self.message_fa,
            "context": self.context,
        }


class If97RangeError(DomainError):
    """Requested state point is outside the IAPWS-IF97 validity range."""

    def __init__(self, p_bar: float, t_c: float, detail: str = "") -> None:
        super().__init__(
            "out_of_if97_range",
            context={"P_bar": p_bar, "T_C": t_c, "detail": detail},
        )
