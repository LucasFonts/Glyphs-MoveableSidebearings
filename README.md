# Mouse Kerning and Spacing a.k.a. DragToKern

Apply kerning and edit spacing by dragging glyphs with your mouse.

_Mouse Kerning and Spacing_ is a tool plugin. Activate it by pressing the
shortcut key _K_ or by clicking the toolbar icon that shows _kTd_. Double-click
a glyph to go back to the _Select_ tool.

The mode of operation is determined by the kerning/spacing icon in the Edit
view.

- ![](media/KerningIconTemplate.png) Kerning mode
- ![](media/KerningIconDisabledTemplate.png) Spacing mode
- ![](media/KerningIconLockedTemplate.png) Spacing is locked

## Kerning Mode

Just drag any glyph in your edit view to adjust its kerning.

![](media/DragToKern.gif)

- Hold **Option** to enable _precision mode_ which increases the mouse sensitivity 10-fold.
- Hold **Shift** to round the kerning values to 10 units.

### Kerning Exceptions

To add or remove kerning exceptions, you can use shortcut keys. The kerning
pair on which those shortcuts operate is always the glyph at the current mouse
position and the glyph to the left of it.

- **A** – Make an exception for the right side of the left glyph
- **S** – Make an exception for the left side of the right glyph
- **D** – Make exceptions for both glyphs
- **Shift+A** – Remove the exception for the right side of the left glyph
- **Shift+S** – Remove the exception for the left side of the right glyph
- **Shift+D** – Remove the exceptions for both glyphs

This is best illustrated with an example:

![](media/DragToKern-Exception.gif)

Hovering over the **ö**, the shortcuts will:

- **A** – Make an exception for the **T** with the **o group**
- **S** – Make an exception for the **T group** with the **ö**
- **D** – Make exceptions for **T** with **ö**
- **Shift+A** – Remove the exception for the **T** with the **o group**
- **Shift+S** – Remove the exception for the **T group** with the **ö**
- **Shift+D** – Remove the exceptions for **T** with **ö**

## Spacing Mode

Hover over a glyph’s left or right edge, and red indicators will appear. Click and
drag while the indicators are shown to modify the sidebearings.

![](media/DragToKern-Spacing.gif)

Click and drag while the **Command** key is pressed to move the glyph’s outline
inside its current width.

If the current master’s metrics are linked to another master, dragging the
sidebearing handles does nothing. A small lock is shown when trying to drag.
You can still move the outline inside its current width by holding the
**Command** key.

You can hide or show the measurements shown while dragging via the contextual
menu _(Hide Measurements While Spacing/Show Measurements While Spacing)._

## Known issues

- Metrics keys are not considered when dragging the spacing. The linked metrics
  just go out of sync.
- Undo for metrics and kerning changes only works if you make the affected
  glyph the current glyph (e.g. by double-clicking it with the select tool)

## Copyright

© 2022 by [LucasFonts](https://www.lucasfonts.com/). Main programmer: Jens Kutílek. Licensed under the [MIT license](LICENSE).
