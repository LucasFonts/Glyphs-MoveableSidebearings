# encoding: utf-8
from __future__ import division, print_function, unicode_literals

import objc

from AppKit import NSCursor
from GlyphsApp import Glyphs

try:
    from GlyphsApp import GSLTR as LTR, GSRTL as RTL
except:
    from GlyphsApp import LTR, RTL
from GlyphsApp.plugins import SelectTool


LIVE_UPDATE = True


class DragToKern(SelectTool):
    @objc.python_method
    def settings(self):
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

    def standardCursor(self):
        return self.cursor

    @objc.python_method
    def start(self):
        self.mode = None
        self.drag_start = None
        self.direction = LTR

    @objc.python_method
    def activate(self):
        pass

    @objc.python_method
    def deactivate(self):
        pass

    def keyDown_(self, theEvent):
        c = theEvent.characters()
        if c in ("a", "s", "d", "A", "S", "D"):
            # Get the mouse location and convert it to local coordinates
            evc = self.editViewController()
            gv = evc.graphicView()
            loc = gv.convertPoint_fromView_(theEvent.locationInWindow(), None)
            # Which layer is at the mouse click location?
            layerIndex = gv.layerIndexForPoint_(loc)
            composedLayers = evc.composedLayers
            self.handleException(composedLayers, layerIndex, c)
            return

        # Other keys are handled by the super class
        super(DragToKern, self).keyDown_(theEvent)

    def mouseDown_(self, theEvent):
        """
        Get the mouse down location to record the start coordinate and dragged
        layer.
        """
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

        # What should be modified? Kerning, LSB, RSB, or both SBs?
        wc = self.windowController()
        alt = wc.AltKey()
        cmd = wc.CommandKey()
        if alt:
            if cmd:
                # alt + cmd
                self.mode = "move"
            else:
                self.mode = "LSB"
        elif cmd:
            self.mode = "RSB"
        else:
            # No modifiers
            self.mode = "kern"

        composedLayers = evc.composedLayers

        if layerIndex > 0xFFFF:
            # No layer (maxint) can't be modified
            self.cancel_operation()
            return

        if self.mode == "kern":
            # Kerning between two glyphs will be modified
            if layerIndex == 0 or not gv.doKerning():
                # First layer (0) or no layer (maxint) can't be kerned
                # Don't edit if kerning is not shown in the view
                self.cancel_operation()
                # self.setLockedCursor()
                return

            # Find out which layers should be kerned
            self.layer1 = composedLayers[layerIndex - 1]
            self.layer2 = composedLayers[layerIndex]
            if self.layer2.master != self.layer1.master:
                # Can't add kerning between different masters
                self.cancel_operation()
                # self.setLockedCursor()
                return

        else:
            # Metrics of one glyph will be modified
            if not gv.doSpacing() and self.mode != "move":
                # Don't edit if spacing is locked in the view
                self.cancel_operation()
                # self.setLockedCursor()
                return

            self.layer2 = composedLayers[layerIndex]

        self.layer2.parent.beginUndo()

    @objc.python_method
    def cancel_operation(self):
        self.layer1 = None
        self.layer2 = None
        self.drag_start = None

    @objc.python_method
    def setLockedCursor(self):
        # self.editViewController().contentView().enclosingScrollView().setDocumentCursor_(self.lckCursor)
        pass

    @objc.python_method
    def setStdCursor(self):
        # self.editViewController().contentView().enclosingScrollView().setDocumentCursor_(self.stdCursor)
        pass

    def mouseDragged_(self, theEvent):
        """
        Update the kerning when the mouse is dragged and live update is on.
        """
        if not LIVE_UPDATE:
            return

        if self.drag_start is None:
            return

        needsRedraw = self.handleDrag(theEvent)
        if needsRedraw:
            self.editViewController().forceRedraw()

    def mouseUp_(self, theEvent):
        """
        If live update is off, we must update the kerning on mouse up.
        """
        needsRedraw = False
        if not LIVE_UPDATE:
            if self.drag_start is None:
                self.cancel_operation()
                return

            needsRedraw = self.handleDrag(theEvent)

        if self.layer2 is not None:
            self.layer2.parent.endUndo()
            if needsRedraw:
                self.editViewController().forceRedraw()

        self.direction = LTR
        self.mode = None
        self.cancel_operation()
        # self.setStdCursor()

    @objc.python_method
    def metricsAreLocked(self, layer):
        cp1 = "Link Metrics With First Master"
        cp2 = "Link Metrics With Master"
        if (
            cp1 in layer.master.customParameters
            or cp2 in layer.master.customParameters
        ):
            return True
        return False

    @objc.python_method
    def handleDrag(self, theEvent):
        """
        Get the current location while the mouse is dragging. Returns True if
        the view needs a redraw, i.e. the kerning or metrics were modified.
        """
        if self.layer2 is None:
            return
        if self.drag_start is None:
            return

        evc = self.editViewController()
        gv = evc.graphicView()
        loc = gv.convertPoint_fromView_(theEvent.locationInWindow(), None)
        delta = int(round((loc.x - self.drag_start.x) / evc.scale))
        self.drag_start = loc
        if delta != 0:
            # Only "move" can be applied for linked metrics
            if self.mode == "move":
                self.layer2.LSB += delta
                self.layer2.width -= delta
                return True

            if self.metricsAreLocked(self.layer2):
                return False

            if self.mode == "kern":
                self.applyKerning(
                    self.layer1, self.layer2, delta, self.direction
                )
                return False  # Kerning changes already trigger a redraw

            if self.mode == "LSB":
                self.layer2.LSB += delta
                return True

            if self.mode == "RSB":
                self.layer2.RSB += delta
                return True

        return False

    @objc.python_method
    def handleException(self, composedLayers, layerIndex, c):
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
            return False

        if c == "d":
            # Both layers should get the exception
            layer1.setNextKerningExeption_forLayer_direction_(
                True, layer2, self.direction
            )
            layer2.setPreviousKerningExeption_forLayer_direction_(
                True, layer1, self.direction
            )
        elif c == "a":
            # First layer should get exception
            layer1.setNextKerningExeption_forLayer_direction_(
                True, layer2, self.direction
            )
        elif c == "s":
            # First layer should get exception
            layer2.setPreviousKerningExeption_forLayer_direction_(
                True, layer1, self.direction
            )
        elif c == "D":
            # Remove kerning exception for both layers
            layer1.setNextKerningExeption_forLayer_direction_(
                False, layer2, self.direction
            )
            layer2.setPreviousKerningExeption_forLayer_direction_(
                False, layer1, self.direction
            )
        elif c == "A":
            # Remove kerning exception for first layer
            layer1.setNextKerningExeption_forLayer_direction_(
                False, layer2, self.direction
            )
        elif c == "S":
            # Remove kerning exception for second layer
            layer2.setPreviousKerningExeption_forLayer_direction_(
                False, layer1, self.direction
            )
        else:
            return False
        return True

    @objc.python_method
    def applyKerning(self, layer1, layer2, delta, direction=LTR):
        """
        Apply the kerning difference to the given layer pair.
        """
        value = layer2.previousKerningForLayer_direction_(layer1, direction)

        # Glyphs 3 returns "no kerning" as None, Glyphs 2 as maxint
        if value is None or value > 0xFFFF:
            # Kern pair didn't exist, set the kerning to the delta value
            value = delta
        else:
            # Kern pair existed before, add the delta value
            value += delta

        # print(layer1.parent.name, layer2.parent.name, value, delta, direction)

        if direction == LTR:
            layer2.setPreviousKerning_forLayer_direction_(
                value, layer1, direction
            )
        else:
            layer2.setPreviousKerning_forLayer_direction_(
                value, layer1, direction
            )

    def drawLayer_atPoint_asActive_attributes_(
        self, layer, layerOrigin, active, attributes
    ):
        gv = self.editViewController().graphicView()
        gv.drawLayer_atPoint_asActive_attributes_(
            layer, layerOrigin, active, attributes
        )

    def drawMetricsForLayer_atPoint_asActive_(
        self, layer, layerOrigin, active
    ):
        pass

    @objc.python_method
    def __file__(self):
        """Please leave this method unchanged"""
        return __file__
