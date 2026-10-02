"""Tests for queue filtering and search (roadmap: richer queue filtering)."""

from unittest.mock import MagicMock, patch

import pytest

from views.queue_view import QueueView


def _make_view(items):
    manager = MagicMock()
    manager.get_all.return_value = items
    view = QueueView(
        manager,
        on_cancel=MagicMock(),
        on_remove=MagicMock(),
        on_reorder=MagicMock(),
        on_play=MagicMock(),
        on_open_folder=MagicMock(),
    )
    view.page = MagicMock()
    return view, manager


ITEMS = [
    {"id": "1", "title": "Alpha video", "url": "https://a/1", "status": "Downloading"},
    {"id": "2", "title": "Beta song", "url": "https://b/2", "status": "Queued"},
    {"id": "3", "title": "Gamma clip", "url": "https://c/3", "status": "Completed"},
    {"id": "4", "title": "Delta fail", "url": "https://d/4", "status": "Error"},
    {"id": "5", "title": "Epsilon hold", "url": "https://e/5", "status": "Paused"},
]


class TestQueueFiltering:
    def test_default_shows_everything(self):
        view, _ = _make_view(ITEMS)
        with patch("views.queue_view.DownloadItemControl") as control:
            view.rebuild()

        assert control.call_count == len(ITEMS)

    @pytest.mark.parametrize(
        ("status_filter", "expected_ids"),
        [
            ("active", {"1"}),
            ("queued", {"2", "5"}),
            ("completed", {"3"}),
            ("failed", {"4"}),
            ("all", {"1", "2", "3", "4", "5"}),
        ],
    )
    def test_status_filters(self, status_filter, expected_ids):
        view, _ = _make_view(ITEMS)
        view._status_filter = status_filter

        with patch("views.queue_view.DownloadItemControl") as control:
            view.rebuild()

        rendered = {call.args[0]["id"] for call in control.call_args_list}
        assert rendered == expected_ids

    def test_search_matches_title_case_insensitively(self):
        view, _ = _make_view(ITEMS)
        view._search_filter = "alpha"

        with patch("views.queue_view.DownloadItemControl") as control:
            view.rebuild()

        assert control.call_count == 1
        assert control.call_args.args[0]["id"] == "1"

    def test_search_matches_url(self):
        view, _ = _make_view(ITEMS)
        view._search_filter = "c/3"

        with patch("views.queue_view.DownloadItemControl") as control:
            view.rebuild()

        assert control.call_count == 1
        assert control.call_args.args[0]["id"] == "3"

    def test_filters_combine(self):
        view, _ = _make_view(ITEMS)
        view._status_filter = "queued"
        view._search_filter = "beta"

        with patch("views.queue_view.DownloadItemControl") as control:
            view.rebuild()

        assert control.call_count == 1
        assert control.call_args.args[0]["id"] == "2"

    def test_empty_result_shows_filtered_message(self):
        view, _ = _make_view(ITEMS)
        view._status_filter = "failed"
        view._search_filter = "nothing-matches"

        view.rebuild()

        assert len(view.list_view.controls) == 1
        placeholder = view.list_view.controls[0]
        text_controls = [
            control
            for control in placeholder.content.controls
            if hasattr(control, "value") and isinstance(control.value, str)
        ]
        assert text_controls, "empty state must render a message"
        assert "nothing-matches" in text_controls[0].value

    def test_empty_queue_message_is_unchanged(self):
        view, _ = _make_view([])
        view.rebuild()

        placeholder = view.list_view.controls[0]
        text_controls = [
            control
            for control in placeholder.content.controls
            if hasattr(control, "value") and isinstance(control.value, str)
        ]
        assert text_controls
        assert "matching" not in text_controls[0].value

    def test_bulk_actions_follow_full_queue_not_filter(self):
        """Filtering must not disable bulk actions for hidden items."""
        view, _ = _make_view(ITEMS)
        view._status_filter = "completed"
        view.rebuild()

        assert view.cancel_all_btn.disabled is False  # downloading item exists
        assert view.pause_all_btn.disabled is False  # queued item exists
        assert view.clear_completed_btn.disabled is False  # error item exists

    def test_changing_filter_resets_selection_and_rebuilds(self):
        view, _ = _make_view(ITEMS)
        view.selected_index = 4
        view.filter_dd.value = "failed"

        view._on_filter_change(None)

        assert view._status_filter == "failed"
        assert view.selected_index == 0

    def test_search_change_is_trimmed_and_lowercased(self):
        view, _ = _make_view(ITEMS)
        view.queue_search.value = "  Alpha  "

        with patch.object(view, "rebuild") as rebuild:
            view._on_queue_search_change(None)

        assert view._search_filter == "alpha"
        rebuild.assert_called_once()

    def test_search_noop_when_unchanged(self):
        view, _ = _make_view(ITEMS)
        view._search_filter = "alpha"
        view.queue_search.value = "Alpha"

        with patch.object(view, "rebuild") as rebuild:
            view._on_queue_search_change(None)

        rebuild.assert_not_called()
