import pytest

from qp_api.llm import get_chat_model


def test_rejects_bad_spec() -> None:
    with pytest.raises(ValueError):
        get_chat_model("gemini-without-provider")
