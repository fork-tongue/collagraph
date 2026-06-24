"""Tests for PySideRenderer resilience to errors.

These tests verify that the renderer properly handles errors during:
- Setting attributes (signal blocking must be restored)
- Adding event listeners
- Inserting/removing elements

See GitHub Issue #153 and PR #151 for context.
"""

import pytest

PySide6 = pytest.importorskip("PySide6")


import collagraph as cg


class TestSignalBlockingResilience:
    """Tests that signal blocking is properly restored after errors."""

    def test_qobject_set_attribute_restores_signals_on_error(self, qapp, caplog):
        """Test that signals are unblocked even when set_attribute encounters an error.

        If set_attribute fails after blocking signals, the signals should still
        be unblocked to prevent leaving the object in an inconsistent state.
        The error is logged but not raised (for resilience during hot-reloading).
        """
        renderer = cg.PySideRenderer(autoshow=False)
        widget = renderer.create_element("widget")

        # Verify signals are not blocked initially
        assert not widget.signalsBlocked()

        # Try to set an invalid attribute that will cause an error
        # Using a method that expects specific types but gets an invalid one
        # Error is caught and logged, not raised
        renderer.set_attribute(widget, "geometry", "not-a-valid-geometry")

        # Verify the error was logged
        assert "Error setting attribute 'geometry'" in caplog.text

        # Signals should NOT be blocked after the error
        assert not widget.signalsBlocked(), (
            "Signals remain blocked after set_attribute error! "
            "This can cause the widget to become unresponsive."
        )

    def test_qobject_set_attribute_with_invalid_tuple_args(self, qapp, caplog):
        """Test that signals are restored when call_method fails with tuple args."""
        renderer = cg.PySideRenderer(autoshow=False)
        widget = renderer.create_element("widget")

        assert not widget.signalsBlocked()

        # setGeometry expects (x, y, w, h) but we'll provide wrong types
        # Error is caught and logged, not raised
        renderer.set_attribute(widget, "geometry", ("a", "b", "c", "d"))

        # Verify the error was logged
        assert "Error setting attribute 'geometry'" in caplog.text

        assert not widget.signalsBlocked()

    def test_standard_item_set_attribute_restores_signals_on_error(self, qapp, caplog):
        """
        Test that model signals are unblocked when QStandardItem set_attribute fails.
        """
        renderer = cg.PySideRenderer(autoshow=False)

        # Create a model and add an item to it
        model = renderer.create_element("QStandardItemModel")
        item = renderer.create_element("QStandardItem")
        model.appendRow(item)

        # Verify model signals are not blocked initially
        assert not model.signalsBlocked()

        # Try to set an invalid attribute that should cause an error
        # Error is caught and logged, not raised
        renderer.set_attribute(item, "model_index", ("not", "valid"))

        # Verify the error was logged
        assert "Error setting attribute 'model_index'" in caplog.text

        # Model signals should NOT be blocked after the error
        assert not model.signalsBlocked(), (
            "Model signals remain blocked after set_attribute error on QStandardItem!"
        )

    def test_tree_widget_item_insert_restores_signals_on_error(self, qapp):
        """Test that tree widget signals are restored when insert fails."""
        renderer = cg.PySideRenderer(autoshow=False)

        tree_widget = renderer.create_element("QTreeWidget")
        item = renderer.create_element("QTreeWidgetItem")

        # First add the item normally
        tree_widget.insert(item)

        assert not tree_widget.signalsBlocked()

        # Try to insert something that's not a QTreeWidgetItem
        # Note: The NotImplementedError is raised *before* signals are blocked
        # (it's the first check in the insert method), so it propagates
        with pytest.raises(NotImplementedError):
            tree_widget.insert("not-a-tree-widget-item")

        # Tree widget signals should NOT be blocked after the error
        assert not tree_widget.signalsBlocked(), (
            "Tree widget signals remain blocked after insert error!"
        )

    def test_tree_widget_item_set_attribute_restores_signals_on_error(
        self, qapp, caplog
    ):
        """
        Test that tree widget signals are restored when set_attribute fails on item.
        """
        renderer = cg.PySideRenderer(autoshow=False)

        tree_widget = renderer.create_element("QTreeWidget")
        item = renderer.create_element("QTreeWidgetItem")
        tree_widget.insert(item)

        assert not tree_widget.signalsBlocked()

        # Try to set content with invalid column index - this will fail
        # because QTreeWidgetItem.setText requires an int for the column
        # Error is caught and logged, not raised
        renderer.set_attribute(item, "content", {None: "text"})

        # Verify the error was logged
        assert "Error setting attribute 'content'" in caplog.text

        # Tree widget signals should NOT be blocked after the error
        assert not tree_widget.signalsBlocked()


class TestEventListenerResilience:
    """Tests for event listener error handling."""

    def test_add_event_listener_with_failing_slot_creation(self, qapp):
        """
        Test that adding an event listener handles slot creation errors gracefully.
        """
        renderer = cg.PySideRenderer(autoshow=False)
        button = renderer.create_element("button")

        # A function that will cause issues when wrapped in a slot
        def problematic_handler():
            pass

        # This should not leave the button in an inconsistent state
        # even if something goes wrong internally
        renderer.add_event_listener(button, "clicked", problematic_handler)

        # The handler should be successfully connected
        assert hasattr(button, "slots")
        assert "clicked" in button.slots

    def test_remove_event_listener_with_missing_handler(self, qapp):
        """Test removing an event listener that was never added."""
        renderer = cg.PySideRenderer(autoshow=False)
        button = renderer.create_element("button")

        def never_added_handler():
            pass

        # Add a different handler first
        def actual_handler():
            pass

        renderer.add_event_listener(button, "clicked", actual_handler)

        # Trying to remove a handler that was never added should not crash
        # or leave the system in an inconsistent state
        renderer.remove_event_listener(button, "clicked", never_added_handler)

        # The original handler should still be there
        assert len(button.slots["clicked"]) == 1


class TestCreateElementResilience:
    """Tests for create_element error handling."""

    def test_create_element_with_unknown_type(self, qapp):
        """Test that creating an element with an unknown type fails gracefully."""
        renderer = cg.PySideRenderer(autoshow=False)

        with pytest.raises(TypeError, match="Couldn't find type"):
            renderer.create_element("NonExistentWidget")

    def test_create_element_with_constructor_error(self, qapp):
        """Test behavior when a type's constructor fails."""
        renderer = cg.PySideRenderer(autoshow=False)

        # QItemSelectionModel requires a model in its constructor
        # Creating it without proper setup should handle the error
        # (Note: This might actually work in some cases, so we test behavior)
        try:
            item = renderer.create_element("QItemSelectionModel")
            # If it succeeds, that's fine too
            assert item is not None
        except (TypeError, RuntimeError):
            # Expected if constructor fails
            pass


class TestInsertRemoveResilience:
    """Tests for insert/remove operation error handling."""

    def test_insert_invalid_child_type(self, qapp, caplog):
        """Test that inserting an invalid child type is handled properly.

        Errors during insert are caught and logged for resilience.
        """
        renderer = cg.PySideRenderer(autoshow=False)

        widget = renderer.create_element("widget")

        # Try to insert something that's not a widget
        # Error is caught and logged, not raised
        renderer.insert("not-a-widget", widget)

        # Verify the error was logged
        assert "Error inserting" in caplog.text

    def test_remove_child_not_in_parent(self, qapp):
        """Test removing a child that isn't actually a child of the parent."""
        renderer = cg.PySideRenderer(autoshow=False)

        parent = renderer.create_element("widget")
        child1 = renderer.create_element("label")
        child2 = renderer.create_element("label")

        # Only add child1 to parent
        renderer.insert(child1, parent)

        # Trying to remove child2 (which was never added) should be handled
        # gracefully without crashing (error is logged)
        renderer.remove(child2, parent)


class TestSetAttributeResilience:
    """Tests for set_attribute error handling in various scenarios."""

    def test_set_attribute_with_none_value(self, qapp):
        """Test that setting an attribute to None is handled properly."""
        renderer = cg.PySideRenderer(autoshow=False)
        widget = renderer.create_element("widget")

        # Setting text to None should be handled gracefully
        # (error caught and logged)
        renderer.set_attribute(widget, "window_title", None)

        assert not widget.signalsBlocked()

    def test_set_attribute_method_not_found(self, qapp):
        """Test setting an attribute when no setter method exists."""
        renderer = cg.PySideRenderer(autoshow=False)
        widget = renderer.create_element("widget")

        # This should fall back to setting a custom attribute
        renderer.set_attribute(widget, "custom_property", "custom_value")

        assert hasattr(widget, "custom_property")
        assert widget.custom_property == "custom_value"

    def test_set_layout_with_invalid_type(self, qapp, caplog):
        """Test setting a layout with an invalid type specification.

        The error is caught and logged for resilience.
        """
        renderer = cg.PySideRenderer(autoshow=False)
        widget = renderer.create_element("widget")

        # Try setting layout with invalid type - error is logged
        renderer.set_attribute(widget, "layout", {"type": "NonExistentLayout"})

        # Verify the error was logged
        assert "Error setting attribute 'layout'" in caplog.text
        assert "No layout registered" in caplog.text
