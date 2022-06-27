# DragToKern

Apply kerning and edit spacing by dragging glyphs with your mouse.

DragToKern is a tool plugin. Activate it by pressing the shortcut key _K_ or by
clicking the toolbar icon that shows _kT_.

Just drag any glyph in your edit view to adjust its kerning.

Despite its name, you can also use this tool to change the spacing by holding
any modifier keys when starting to drag:

- **Option** – Change the left sidebearing
- **Command** – Change the right sidebearing
- **Option + Command** – Move the outline inside its current width

## Known issues

- When modifying the right sidebearing, the preview glyphs do not update
  instantly.
- Each small kerning modification is its own undo step, so when kerning, undo
  is effectively useless.
- Kerning exceptions are not supported. When dragging any existing exception
  pair, the class pair’s kerning is modified instead.
- If the current master’s metrics are linked to another master, dragging does
  nothing.
- Metrics keys are not considered when dragging the spacing. The linked metrics
  just go out of sync.


# MoveableSidebearings

Draggable sidebearings for Glyphs.app. This plugin provides an alternate method
to modify the sidebearings with the mouse. You should probably only use one or
the other plugin.

MoveableSidebearings is a reporter plugin, so it can be activated via the _View_
menu:

_View > Show Moveable Sidebearings_

<img src="media/MetricsHandles.png">

Hover over the sidebearings of the active glyph and drag them to adjust.