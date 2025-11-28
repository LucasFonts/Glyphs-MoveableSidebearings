from __future__ import annotations

from typing import Any

import objc
from AppKit import (
    NSBezierPath,
    NSClassFromString,
    NSColor,
    NSCursor,
    NSFont,
    NSFontAttributeName,
    NSFontWeightRegular,
    NSForegroundColorAttributeName,
    NSGradient,
    NSPoint,
    NSRect,
    NSString,
)
from GlyphsApp import GSLTR, MOUSEMOVED, Glyphs
from GlyphsApp.plugins import SelectTool

GlyphsToolSelect = NSClassFromString("GlyphsToolSelect")

SNAP_TOLERANCE = 14
COLOR_R = 0.9
COLOR_G = 0.1
COLOR_B = 0.0
COLOR_ALPHA = 0.5
DRAGGING_HANDLE_HEIGHT = 30
DRAGGING_HANDLE_WIDTH = 1
LABEL_TEXT_SIZE = 11
LABEL_DIST = 6
LABEL_VERT_INNER_BIAS = 0.3


def applyKerning(layer1, layer2, delta, step, direction=GSLTR) -> None:
    """
    Apply the kerning difference to the given layer pair.
    """
    value = layer2.previousKerningForLayer_direction_(layer1, direction)

    # Glyphs 3 returns "no kerning" as None
    if value is None or value > 0xFFFF:
        # Kern pair didn't exist, set the kerning to the delta value
        value = int(round(delta / step) * step)
    else:
        # Kern pair existed before, add the delta value
        value = int(round((value + delta) / step) * step)

    if direction == GSLTR:
        layer2.setPreviousKerning_forLayer_direction_(value, layer1, direction)
    else:
        layer2.setPreviousKerning_forLayer_direction_(value, layer1, direction)


def handleException(composedLayers, layerIndex, c, direction=GSLTR) -> None:
    """
    Add or remove an exception at the current location
    """
    if layerIndex == 0 or layerIndex > 0xFFFF:
        return

    # Find out which layers should be get the exception
    layer1 = composedLayers[layerIndex - 1]
    layer2 = composedLayers[layerIndex]
    if layer2.master != layer1.master:
        # Can't add kerning between different masters
        return

    if c == "d":
        # Both layers should get the exception
        layer1.setNextKerningExeption_forLayer_direction_(True, layer2, direction)
        layer2.setPreviousKerningExeption_forLayer_direction_(True, layer1, direction)
    elif c == "a":
        # First layer should get exception
        layer1.setNextKerningExeption_forLayer_direction_(True, layer2, direction)
    elif c == "s":
        # First layer should get exception
        layer2.setPreviousKerningExeption_forLayer_direction_(True, layer1, direction)
    elif c == "D":
        # Remove kerning exception for both layers
        layer1.setNextKerningExeption_forLayer_direction_(False, layer2, direction)
        layer2.setPreviousKerningExeption_forLayer_direction_(False, layer1, direction)
    elif c == "A":
        # Remove kerning exception for first layer
        layer1.setNextKerningExeption_forLayer_direction_(False, layer2, direction)
    elif c == "S":
        # Remove kerning exception for second layer
        layer2.setPreviousKerningExeption_forLayer_direction_(False, layer1, direction)


class DragToKern(SelectTool):
    @objc.python_method
    def settings(self) -> None:
        self.name = Glyphs.localize(
            {
                "en": "Mouse Kerning and Spacing",
                "de": "Unterschneidung und Zurichtung per Maus",
            }
        )
        self.keyboardShortcut = "k"
        self.stdCursor = NSCursor.resizeLeftRightCursor()
        self.lckCursor = NSCursor.operationNotAllowedCursor()
        self.cursor = self.stdCursor
        self.colorSBOuter = NSColor.colorWithCalibratedRed_green_blue_alpha_(
            COLOR_R, COLOR_G, COLOR_B, COLOR_ALPHA
        )
        self.colorSBInner = NSColor.colorWithCalibratedRed_green_blue_alpha_(
            COLOR_R, COLOR_G, COLOR_B, 0.0
        )
        self.colorLabel = NSColor.textColor()
        self.colorBox = NSColor.textBackgroundColor()

    def standardCursor(self):
        return self.cursor

    @objc.python_method
    def start(self) -> None:
        self.mode: str | None = None
        self.mouse_position = (0, 0)
        self.drag_start = None
        self.direction = GSLTR
        self.active_metric = None
        self.orig_value = None
        self.handle_x = None
        self.width = None
        self.layer1 = None
        self.layer2 = None
        self.drawMeasurements = Glyphs.defaults[
            "com.lucasfonts.DragToKern.measurements"
        ]
        if self.drawMeasurements is None:
            self.drawMeasurements = False

    @objc.python_method
    def activate(self) -> None:
        Glyphs.addCallback(self.mouseDidMove, MOUSEMOVED)
        self.drawMeasurements = Glyphs.defaults[
            "com.lucasfonts.DragToKern.measurements"
        ]

    @objc.python_method
    def deactivate(self) -> None:
        Glyphs.removeCallback(self.mouseDidMove, MOUSEMOVED)
        Glyphs.defaults["com.lucasfonts.DragToKern.measurements"] = (
            self.drawMeasurements
        )

    @objc.python_method
    def conditionalContextMenus(self) -> list[dict[str, Any]]:
        if self.drawMeasurements:
            return [
                {
                    "name": Glyphs.localize(
                        {
                            "en": "Hide Measurements While Spacing",
                        }
                    ),
                    "action": self.toggleMeasurements_,
                }
            ]
        return [
            {
                "name": Glyphs.localize(
                    {
                        "en": "Show Measurements While Spacing",
                    }
                ),
                "action": self.toggleMeasurements_,
            }
        ]

    def toggleMeasurements_(self, sender=None) -> None:
        self.drawMeasurements = not self.drawMeasurements

    @objc.python_method
    def doKerning(self, graphicView) -> bool:
        return graphicView.doKerning()

    @objc.python_method
    def doSpacing(self, graphicView) -> bool:
        return not graphicView.doKerning() and graphicView.doSpacing()

    def keyDown_(self, theEvent) -> None:
        c = theEvent.characters()
        if c in ("a", "s", "d", "A", "S", "D"):
            # Get the mouse location and convert it to local coordinates
            evc = self.editViewController()
            gv = evc.graphicView()
            loc = gv.convertPoint_fromView_(theEvent.locationInWindow(), None)
            # Which layer is at the mouse click location?
            layerIndex = gv.layerIndexForPoint_(loc)
            composedLayers = evc.composedLayers
            handleException(composedLayers, layerIndex, c, self.direction)
            return

        # Other keys are handled by the super class
        objc.super().keyDown_(theEvent)

    @objc.python_method
    def mouseDidMove(self, notification) -> None:
        Glyphs.redraw()

    def mouseDown_(self, theEvent) -> None:
        """
        Get the mouse down location to record the start coordinate and dragged
        layer.
        """
        if theEvent.clickCount() == 2:
            wc = self.windowController()
            wc.setToolForClass_(GlyphsToolSelect)
            toolDelegate = wc.toolEventDelegate()
            if toolDelegate.respondsToSelector_("selectGlyph:"):
                toolDelegate.selectGlyph_(theEvent)
            return
        # Get the mouse click location and convert it to local coordinates
        evc = self.editViewController()
        gv = evc.graphicView()
        loc = gv.convertPoint_fromView_(theEvent.locationInWindow(), None)
        # Which layer is at the mouse click location?
        layerIndex = gv.layerIndexForPoint_(loc)
        # Note the start coordinates for later
        self.drag_start = loc
        # Note the kerning direction
        self.direction = evc.direction

        if layerIndex > 0xFFFF:
            # No layer (maxint) can't be modified
            self.setLockedCursor()
            self.cancel_operation()
            return

        # Collect some info about the clicked layer
        composedLayers = evc.composedLayers
        self.layer2 = composedLayers[layerIndex]
        layerOrigin = gv.cachedPositionAtIndex_(layerIndex)

        # What should be modified? Kerning, LSB, RSB, or both SBs?

        spacing = self.doSpacing(gv)
        kerning = self.doKerning(gv)
        if spacing:
            # Check if the click was at a sidebearing handle
            result = self.checkHandleLocation(loc, gv, self.layer2, layerOrigin)

            if result is None:
                self.active_metric = None
            else:
                self.active_metric = result[0][0]

            if self.windowController().CommandKey():
                self.mode = "move"
            elif self.active_metric == "LSB":
                self.mode = "LSB"
                if self.layer2 is None:
                    return
                self.orig_value = self.layer2.LSB
            elif self.active_metric == "RSB":
                self.mode = "RSB"
                if self.layer2 is None:
                    return
                self.orig_value = self.layer2.RSB
            elif kerning:
                if not self.setupKerning(composedLayers, layerIndex):
                    return
            else:
                self.setLockedCursor()
                self.cancel_operation()
                return

        elif kerning:
            if not self.setupKerning(composedLayers, layerIndex):
                return

        if self.layer2 is not None:
            self.layer2.parent.beginUndo()
        Glyphs.redraw()

    @objc.python_method
    def setupKerning(self, composedLayers, layerIndex) -> bool:
        if self.layer2 is None:
            return False

        # Kerning between two glyphs will be modified
        if layerIndex == 0:
            # First layer (0) can't be kerned
            self.setLockedCursor()
            self.cancel_operation()
            return False

        # Find out which layers should be kerned
        self.layer1 = composedLayers[layerIndex - 1]
        # self.layer2 = composedLayers[layerIndex]
        if self.layer2.master != self.layer1.master:
            # Can't add kerning between different masters
            self.setLockedCursor()
            self.cancel_operation()
            return False

        self.mode = "kern"
        return True

    def cancelOperation_(self, sender) -> None:
        wc = self.windowController()
        wc.setToolForClass_(GlyphsToolSelect)

    @objc.python_method
    def cancel_operation(self) -> None:
        self.layer1 = None
        self.layer2 = None
        self.drag_start = None
        self.orig_value = None

    @objc.python_method
    def setLockedCursor(self) -> None:
        # self.editViewController().contentView().enclosingScrollView().setDocumentCursor_(self.lckCursor)
        pass

    @objc.python_method
    def setStdCursor(self) -> None:
        # self.editViewController().contentView().enclosingScrollView().setDocumentCursor_(self.stdCursor)
        pass

    def mouseDragged_(self, theEvent) -> None:
        """
        Update the kerning when the mouse is dragged and live update is on.
        """
        if self.drag_start is None:
            return

        needsRedraw = self.handleDrag(theEvent)
        if needsRedraw:
            self.editViewController().forceRedraw()

    def mouseUp_(self, theEvent) -> None:
        """
        End the undo and reset variables when the mouse is released
        """
        if self.layer2 is not None:
            self.layer2.parent.endUndo()

        self.direction = GSLTR
        self.mode = None
        self.cancel_operation()
        self.setStdCursor()
        self.active_metric = None
        Glyphs.redraw()

    @objc.python_method
    def metricsAreLocked(self, layer) -> bool:
        cp1 = "Link Metrics With First Master"
        cp2 = "Link Metrics With Master"
        if cp1 in layer.master.customParameters or cp2 in layer.master.customParameters:
            return True
        return False

    @objc.python_method
    def handleDrag(self, theEvent) -> bool:
        """
        Get the current location while the mouse is dragging. Returns True if
        the view needs a redraw, i.e. the kerning or metrics were modified.
        """
        if self.layer2 is None:
            return False
        if self.drag_start is None:
            return False

        evc = self.editViewController()
        gv = evc.graphicView()
        loc = gv.convertPoint_fromView_(theEvent.locationInWindow(), None)
        wc = self.windowController()

        # Alt key enables "precision dragging"
        if wc.AltKey():
            mouseZoom = 0.1
        else:
            mouseZoom = 1

        # Shift key rounds to 10
        if wc.ShiftKey():
            step = 10
        else:
            step = 1

        delta = (loc.x - self.drag_start.x) / evc.scale * mouseZoom

        self.drag_start = loc
        if delta != 0.0:
            # Only "move" can be applied for linked metrics
            if self.mode == "move":
                self.layer2.LSB += int(round(delta))
                self.layer2.width -= int(round(delta))
                return True

            if self.metricsAreLocked(self.layer2):
                return False

            if self.mode == "kern":
                applyKerning(self.layer1, self.layer2, delta, step, self.direction)
                return False  # Kerning changes already trigger a redraw

            if self.mode == "LSB":
                self.layer2.LSB += int(round(delta))
                return True

            if self.mode == "RSB":
                self.layer2.RSB += int(round(delta))
                return True

        return False

    def drawLayer_atPoint_asActive_attributes_(
        self, layer, layerOrigin, active, attributes
    ) -> None:
        gv = self.editViewController().graphicView()
        gv.drawLayer_atPoint_asActive_attributes_(
            layer, layerOrigin, active, attributes
        )
        if not self.doSpacing(gv):
            # Not in spacing mode
            return

        if self.drag_start is None:
            result = self.checkHandles(gv, layer, layerOrigin)
            if result is not None:
                metric, handle_x, width = result
                self._drawHandle(handle_x, metric)
        elif self.drawMeasurements:
            self._drawDraggingMeasurements(self.mode, gv, layer, layerOrigin)

    def drawMetricsForLayer_atPoint_asActive_(self, layer, layerOrigin, active) -> None:
        pass

    @objc.python_method
    def checkHandles(
        self, graphicView, layer, layerOrigin
    ) -> tuple[tuple[str, float, float, float, float], tuple[float, float], int] | None:
        """
        Check if the mouse pointer is at a possible metrics handle location.
        Called on MOUSEMOVED via drawLayer_atPoint_asActive_attributes_.
        """
        theEvent = Glyphs.currentEvent()
        if theEvent is None:
            return None

        self.mouse_position = graphicView.convertPoint_fromView_(
            theEvent.locationInWindow(), None
        )
        return self.checkHandleLocation(
            self.mouse_position, graphicView, layer, layerOrigin
        )

    @objc.python_method
    def checkHandleLocation(
        self, location, graphicView, layer, layerOrigin
    ) -> tuple[tuple[str, float, float, float, float], tuple[float, float], int] | None:
        """
        Check if the location of an event is at a possible metrics handle
        location.
        """
        if not self.doSpacing(graphicView):
            return None

        try:
            master = layer.master
        except KeyError:
            return None

        x, y = location
        scale = graphicView.scale()
        desc = master.descender * scale
        asc = master.ascender * scale
        asc += layerOrigin.y
        desc += layerOrigin.y
        layerWidth = layer.width * scale

        # Don't draw handles outside ascender/descender
        if y < desc or y > asc:
            return None

        offsetX = x - layerOrigin.x

        if offsetX < 0 or offsetX > layerWidth:
            # Mouse is outside the glyph
            return None

        if offsetX > SNAP_TOLERANCE and offsetX < layerWidth - SNAP_TOLERANCE:
            # Mouse is too far inside the glyph
            return None

        if offsetX < SNAP_TOLERANCE:
            handle_x = (layerOrigin.x, SNAP_TOLERANCE)
            metric = (
                "LSB",
                layer.LSB,
                layer,
                desc,
                asc,
            )
            width = layerOrigin.x
        else:
            handle_x = (
                layerOrigin.x + layerWidth - SNAP_TOLERANCE,
                SNAP_TOLERANCE,
            )
            metric = (
                "RSB",
                layer.RSB,
                layer,
                desc,
                asc,
            )
            width = layerOrigin.x + layerWidth
        return metric, handle_x, width

    @objc.python_method
    def _drawHandle(self, handle_x, metric) -> None:
        if handle_x is None:
            return
        if metric is None:
            return

        pos, w = handle_x
        metric_name, value, layer, desc, asc = metric
        gradient = NSGradient.alloc().initWithStartingColor_endingColor_(
            self.colorSBOuter, self.colorSBInner
        )
        rect = NSRect(
            origin=(pos, desc),
            size=(w, asc - desc),
        )
        angle = -180 if metric_name == "RSB" else 0
        bezierPath = NSBezierPath.bezierPathWithRect_(rect)
        gradient.drawInBezierPath_angle_(bezierPath, angle)

    @objc.python_method
    def _drawDraggingMeasurements(
        self, metric, graphicView, layer, layerOrigin
    ) -> None:
        if layer != self.layer2 or self.layer2 is None:
            # Only draw labels at the layer being modified
            return

        try:
            master = self.layer2.master
        except KeyError:
            return

        scale = graphicView.scale()
        desc = master.descender * scale
        asc = master.ascender * scale
        asc += layerOrigin.y
        desc += layerOrigin.y
        layerWidth = layer.width * scale
        locked = self.metricsAreLocked(self.layer2)

        if metric in ("LSB", "RSB", "move"):
            # Draw left and right
            x1 = layerOrigin.x - DRAGGING_HANDLE_WIDTH * 0.5
            x2 = layerOrigin.x + layerWidth - DRAGGING_HANDLE_WIDTH * 0.5
            self._drawDraggingTextLabel("LSB", x1, asc, locked)
            self._drawDraggingTextLabel("RSB", x2, asc, locked)
            pos = [x1, x2]
        elif metric == "kern":
            # FIXME: This code is never called
            # Draw left
            x = layerOrigin.x - DRAGGING_HANDLE_WIDTH * 0.5
            self._drawDraggingTextLabel("LSB", x, asc, locked)
            pos = [x]
        else:
            return

        self._drawDraggingMeasurement(pos, asc, desc)

    @objc.python_method
    def _drawDraggingMeasurement(self, xPositions, asc, desc) -> None:
        top = DRAGGING_HANDLE_HEIGHT * LABEL_VERT_INNER_BIAS
        bot = DRAGGING_HANDLE_HEIGHT - top
        for x in xPositions:
            bezierPath = NSBezierPath.bezierPathWithRect_(
                NSRect(
                    origin=(x, desc - bot),
                    size=(DRAGGING_HANDLE_WIDTH, DRAGGING_HANDLE_HEIGHT),
                )
            )
            bezierPath.appendBezierPathWithRect_(
                NSRect(
                    origin=(x, asc - top),
                    size=(DRAGGING_HANDLE_WIDTH, DRAGGING_HANDLE_HEIGHT),
                )
            )
            self.colorSBOuter.set()
            bezierPath.fill()

    @objc.python_method
    def _drawDraggingTextLabel(self, metric, xPosition, asc, locked) -> None:
        if self.layer2 is None:
            return

        if locked:
            shown_value = "🔒︎"
        else:
            if metric == "LSB":
                shown_value = "%g" % self.layer2.LSB
            elif metric == "RSB":
                shown_value = "%g" % self.layer2.RSB
            else:
                return

        attrs = {
            NSFontAttributeName: NSFont.monospacedDigitSystemFontOfSize_weight_(
                LABEL_TEXT_SIZE, NSFontWeightRegular
            ),
            NSForegroundColorAttributeName: self.colorLabel,
        }
        myString = NSString.string().stringByAppendingString_(shown_value)
        bbox = myString.sizeWithAttributes_(attrs)
        bw = bbox.width
        bh = bbox.height
        text_pt = NSPoint()
        text_pt.y = (
            asc
            + DRAGGING_HANDLE_HEIGHT
            - DRAGGING_HANDLE_HEIGHT * LABEL_VERT_INNER_BIAS
            - bh
        )
        if metric == "LSB":
            text_pt.x = xPosition + LABEL_DIST
        elif metric == "RSB":
            text_pt.x = xPosition - LABEL_DIST - bw
        else:
            return

        rect = NSRect(origin=(text_pt.x, text_pt.y), size=(bw, bh))
        outer = NSRect(origin=(text_pt.x - 2, text_pt.y - 1), size=(bw + 4, bh + 2))
        self.colorBox.set()
        NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(outer, 4, 4).fill()
        myString.drawInRect_withAttributes_(rect, attrs)

    @objc.python_method
    def __file__(self) -> str:
        """Please leave this method unchanged"""
        return __file__
