# encoding: utf-8
from __future__ import division, print_function, unicode_literals

import objc

from GlyphsApp import Glyphs
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

    @objc.python_method
    def start(self):
        self.mode = None
        self.drag_start = None

    @objc.python_method
    def activate(self):
        pass

    @objc.python_method
    def deactivate(self):
        pass

    def mouseDown_(self, theEvent):
        """
        Get the mouse down location to record the start coordinate and dragged
        layer.
        """
        # Get the mouse click location and convert it to local coordinates
        gv = self.editViewController().graphicView()
        loc = gv.convertPoint_fromView_(theEvent.locationInWindow(), None)
        # Which layer is at the mouse click location?
        layerIndex = gv.layerIndexForPoint_(loc)
        # Note the start coordinates for later
        self.drag_start = loc

        # What should be modified? Kerning, LSB, RSB, or both SBs?
        alt = self.windowController().AltKey()
        cmd = self.windowController().CommandKey()
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

        if self.mode == "kern":
            # Kerning between two glyphs will be modified
            if layerIndex == 0 or layerIndex > 0xFFFF:
                # First layer (0) or no layer (maxint) can't be kerned
                self.layer1 = None
                self.layer2 = None
                self.drag_start = None
                return

            # Find out which layers should be kerned
            layers = self.editViewController().composedLayers
            self.layer1 = layers[layerIndex - 1]
            self.layer2 = layers[layerIndex]
            if self.layer2.master != self.layer1.master:
                # Can't add kerning between different masters
                self.layer1 = None
                self.layer2 = None
                self.drag_start = None
                return
            return
        
        # Metrics of one glyph will be modified
        if layerIndex > 0xFFFF:
            # No layer (maxint) can't be modified
            self.layer1 = None
            self.layer2 = None
            self.drag_start = None
            return

        layers = self.editViewController().composedLayers
        self.layer1 = layers[layerIndex]
        # print(self.layer1.parent.name, self.mode)
        if self.layer1 is not None:
            self.layer1.parent.beginUndo()

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
                self.layer1 = None
                self.layer2 = None
                return
            
            needsRedraw = self.handleDrag(theEvent)

        self.drag_start = None
        self.layer2 = None
        if self.mode == "kern" or self.mode is None:
            self.layer1 = None
            self.mode = None
            return

        # For sidebearing modifications, end the undo block
        if self.layer1 is not None:
            self.layer1.parent.endUndo()
            if needsRedraw:
                self.editViewController().forceRedraw()

        self.layer1 = None
        self.mode = None

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
        Get the current location while the mouse is dragging.
        """
        if self.layer1 is None:
            return

        evc = self.editViewController()
        gv = evc.graphicView()
        loc = gv.convertPoint_fromView_(theEvent.locationInWindow(), None)
        delta = int(round((loc.x - self.drag_start.x) / evc.scale))
        self.drag_start = loc
        if delta != 0:
            # Only "move" can be applied for linked metrics
            if self.mode == "move":
                self.layer1.LSB += delta
                self.layer1.width -= delta
                return True

            if self.metricsAreLocked(self.layer1):
                return False

            if self.mode == "kern":
                self.applyKerning(self.layer1, self.layer2, delta)
                return False
            
            if self.mode == "LSB":
                self.layer1.LSB += delta
                return True
            
            if self.mode == "RSB":
                self.layer1.RSB += delta
                return True

        return False

    @objc.python_method
    def applyKerning(self, layer1, layer2, delta):
        """
        Apply the kerning difference to the given layer pair.
        """
        # TODO: Support RTL kerning

        # layer1Exception = self.windowController().AltKey()
        # layer2Exception = self.windowController().CommandKey()
        # master = layer2.master
        # masterId = master.id
        # font = master.font

        # glyph1Key = layer1.parent.rightKerningKey
        # glyph2Key = layer2.parent.leftKerningKey

        # classKerning = font.kerningForPair(masterId, glyph1Key, glyph2Key)

        kerning = layer2.previousKerningForLayer_direction_(layer1, 0)  # 0 is LTR
        # Glyphs 3 returns "no kerning" as None, Glyphs 2 as maxint
        if kerning is None or kerning > 0xFFFF:
            kerning = delta
        else:
            kerning += delta

        # # If modifier keys are pressed, make an exception
        # if layer1Exception:
        #     glyph1Key = layer1.parent.name
        # if layer2Exception:
        #     glyph2Key = layer2.parent.name

        # font.setKerningForPair(
        #     masterId,
        #     glyph1Key,
        #     glyph2Key,
        #     kerning,
        # )
        layer2.setPreviousKerning_forLayer_direction_(kerning, layer1, 0)

    def drawLayer_atPoint_asActive_attributes_(self, layer, layerOrigin, active, attributes):
        gv = self.editViewController().graphicView()
        gv.drawLayer_atPoint_asActive_attributes_(layer, layerOrigin, active, attributes)

    def drawMetricsForLayer_atPoint_asActive_(self, layer, layerOrigin, active):
        pass

    @objc.python_method
    def __file__(self):
        """Please leave this method unchanged"""
        return __file__
