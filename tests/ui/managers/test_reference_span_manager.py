import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QListWidgetItem

from ui.managers.plot_tab_managers.reference_span_manager import ReferenceSpanManager

@pytest.fixture
def mock_plot_tab():
    tab = MagicMock()
    view = MagicMock()

    view.annotations_tab.ref_span_type_combo.currentText.return_value = "Horizontal (axhspan)"
    view.annotations_tab.ref_span_ymin_spin.value.return_value = 1.0
    view.annotations_tab.ref_span_ymax_spin.value.return_value = 5.0
    view.annotations_tab.ref_span_xmin_spin.value.return_value = 10.0
    view.annotations_tab.ref_span_xmax_spin.value.return_value = 20.0
    view.annotations_tab.ref_span_alpha_spin.value.return_value = 0.4
    view.annotations_tab.ref_span_label_input.text.return_value = "Test Span"

    view.annotations_tab.reference_spans_list = MagicMock()
    view.annotations_tab.update_ref_span_button = MagicMock()
    view.annotations_tab.delete_ref_span_button = MagicMock()

    tab.view = view
    tab.plot_engine.current_ax = MagicMock()
    tab.status_bar = MagicMock()

    return tab

@pytest.fixture
def span_manager(mock_plot_tab):
    manager = ReferenceSpanManager(mock_plot_tab)
    manager.ref_span_color = "#FF0000"
    return manager

def test_initialization(span_manager):
    """Test that the manager initializes with empty state."""
    assert len(span_manager.reference_spans) == 0
    assert span_manager.selected_ref_span_index == -1

def test_add_horizontal_span(span_manager, mock_plot_tab):
    """Test adding a horizontal span stores correct data and updates UI."""
    mock_plot_tab.view.annotations_tab.ref_span_type_combo.currentText.return_value = "Horizontal (axhspan)"

    span_manager.add_reference_span()

    assert len(span_manager.reference_spans) == 1
    span_data = span_manager.reference_spans[0]

    assert span_data["type"] == "hspan"
    assert span_data["ymin"] == 1.0
    assert span_data["ymax"] == 5.0
    assert span_data["color"] == "#FF0000"
    assert span_data["alpha"] == 0.4
    assert span_data["label"] == "Test Span"

    # Verify UI updates
    mock_plot_tab.view.annotations_tab.reference_spans_list.addItem.assert_called_once()
    mock_plot_tab.on_style_changed.assert_called_once()

def test_add_vertical_span(span_manager, mock_plot_tab):
    """Test adding a vertical span stores correct data."""
    mock_plot_tab.view.annotations_tab.ref_span_type_combo.currentText.return_value = "Vertical (axvspan)"

    span_manager.add_reference_span()

    assert len(span_manager.reference_spans) == 1
    span_data = span_manager.reference_spans[0]

    assert span_data["type"] == "vspan"
    assert span_data["xmin"] == 10.0
    assert span_data["xmax"] == 20.0

def test_select_reference_span(span_manager, mock_plot_tab):
    """Test selecting a span from the list populates the editor."""
    span_manager.add_reference_span()  # Adds a span at index 0

    mock_item = MagicMock(spec=QListWidgetItem)
    mock_plot_tab.view.annotations_tab.reference_spans_list.row.return_value = 0

    span_manager.on_reference_span_selected(mock_item)

    assert span_manager.selected_ref_span_index == 0
    mock_plot_tab.view.annotations_tab.update_ref_span_button.setEnabled.assert_called_with(True)
    mock_plot_tab.view.annotations_tab.delete_ref_span_button.setEnabled.assert_called_with(True)
    mock_plot_tab.view.annotations_tab.ref_span_ymin_spin.setValue.assert_called_with(1.0)

def test_update_reference_span(span_manager, mock_plot_tab):
    """Test modifying properties of an existing span."""
    span_manager.add_reference_span()
    span_manager.selected_ref_span_index = 0

    # Change mock UI values for the update
    mock_plot_tab.view.annotations_tab.ref_span_type_combo.currentText.return_value = "Vertical (axvspan)"
    mock_plot_tab.view.annotations_tab.ref_span_xmin_spin.value.return_value = -5.0
    mock_plot_tab.view.annotations_tab.ref_span_xmax_spin.value.return_value = 5.0
    mock_plot_tab.view.annotations_tab.ref_span_alpha_spin.value.return_value = 0.8
    span_manager.ref_span_color = "#00FF00"

    span_manager.update_selected_reference_span()

    updated_data = span_manager.reference_spans[0]
    assert updated_data["type"] == "vspan"
    assert updated_data["xmin"] == -5.0
    assert updated_data["xmax"] == 5.0
    assert updated_data["alpha"] == 0.8
    assert updated_data["color"] == "#00FF00"

    mock_plot_tab.on_style_changed.assert_called()

def test_delete_reference_span(span_manager, mock_plot_tab):
    """Test deleting a span removes it from tracking and the UI."""
    span_manager.add_reference_span()
    span_manager.selected_ref_span_index = 0

    span_manager.delete_selected_reference_span()

    assert len(span_manager.reference_spans) == 0
    assert span_manager.selected_ref_span_index == -1
    mock_plot_tab.view.annotations_tab.reference_spans_list.takeItem.assert_called_with(0)
    mock_plot_tab.on_style_changed.assert_called()

def test_clear_all_reference_spans(span_manager, mock_plot_tab):
    """Test clearing all spans resets state entirely."""
    span_manager.add_reference_span()
    span_manager.add_reference_span()

    span_manager.clear_all_reference_spans()

    assert len(span_manager.reference_spans) == 0
    mock_plot_tab.view.annotations_tab.reference_spans_list.clear.assert_called_once()
    mock_plot_tab.on_style_changed.assert_called()

def test_apply_reference_spans(span_manager, mock_plot_tab):
    """Test that applying spans calls the correct Matplotlib axes methods."""
    # Add a horizontal span
    mock_plot_tab.view.annotations_tab.ref_span_type_combo.currentText.return_value = "Horizontal (axhspan)"
    span_manager.add_reference_span()

    # Add a vertical span
    mock_plot_tab.view.annotations_tab.ref_span_type_combo.currentText.return_value = "Vertical (axvspan)"
    span_manager.add_reference_span()

    ax_mock = mock_plot_tab.plot_engine.current_ax
    ax_mock.get_children.return_value = []  # No existing children to clear

    span_manager.apply_reference_spans()

    # Check if axhspan was called
    ax_mock.axhspan.assert_called_once_with(
        ymin=1.0,
        ymax=5.0,
        facecolor="#FF0000",
        alpha=0.4,
        label="Test Span",
        gid="ref_span_0",
        edgecolor="none"
    )

    # Check if axvspan was called
    ax_mock.axvspan.assert_called_once_with(
        xmin=10.0,
        xmax=20.0,
        facecolor="#FF0000",
        alpha=0.4,
        label="Test Span",
        gid="ref_span_1",
        edgecolor="none"
    )

def test_apply_removes_old_spans(span_manager, mock_plot_tab):
    """Test that applying spans removes old spans first to prevent stacking."""
    ax_mock = mock_plot_tab.plot_engine.current_ax

    # Mock an existing artist that looks like a reference span
    old_span = MagicMock()
    old_span.get_gid.return_value = "ref_span_0"

    # Mock an artist that is not a span
    other_artist = MagicMock()
    other_artist.get_gid.return_value = "some_other_artist"

    ax_mock.get_children.return_value = [old_span, other_artist]

    span_manager.apply_reference_spans()

    # Ensure the old span was removed, but the other artist was ignored
    old_span.remove.assert_called_once()
    other_artist.remove.assert_not_called()

def test_config_management(span_manager):
    """Test configuration generation and loading."""
    mock_config = [
        {"type": "hspan", "ymin": 0, "ymax": 1, "color": "blue", "alpha": 0.5},
        {"type": "vspan", "xmin": 5, "xmax": 10, "color": "red", "alpha": 0.2}
    ]

    span_manager.load_config(mock_config)
    assert len(span_manager.reference_spans) == 2

    exported_config = span_manager.get_config()
    assert len(exported_config) == 2
    assert exported_config[0]["ymin"] == 0
    assert exported_config[1]["type"] == "vspan"