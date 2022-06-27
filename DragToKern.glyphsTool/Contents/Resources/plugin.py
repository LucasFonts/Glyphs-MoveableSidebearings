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
                "en": "Mouse Kerning",
                "de": "Unterschneidung per Maus",
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

        self.handleDrag(theEvent)
        if self.mode != "kern":
            Glyphs.redraw()

    def mouseUp_(self, theEvent):
        """
        If live update is off, we must update the kerning on mouse up.
        """
        if not LIVE_UPDATE:
            if self.drag_start is None:
                self.layer1 = None
                self.layer2 = None
                return
            
            self.handleDrag(theEvent)

        self.drag_start = None
        self.layer2 = None
        if self.mode == "kern" or self.mode is None:
            self.layer1 = None
            self.mode = None
            return

        # For sidebearing modifications, end the undo block
        if self.layer1 is not None:
            self.layer1.parent.endUndo()
            Glyphs.redraw()

        self.layer1 = None
        self.mode = None

    @objc.python_method
    def metricsAreLocked(self, layer):
        cp1 = "Link Metrics With First Master"
        cp2 = "Link Metrics With Master"
        if (
            cp1 in layer.master.customParameters
            and layer.master.customParameters[cp1] == 1
            or cp2 in layer.master.customParameters
            and layer.master.customParameters[cp2] == 1
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
            if self.mode == "kern":
                self.applyKerning(self.layer1, self.layer2, delta)
                return
            
            if self.metricsAreLocked(self.layer1):
                return

            if self.mode == "LSB":
                self.layer1.LSB += delta
                return
            
            if self.mode == "RSB":
                # FIXME: Doesn't redraw properly
                self.layer1.RSB -= delta
                return

            self.layer1.LSB += delta
            self.layer1.width -= delta

    @objc.python_method
    def applyKerning(self, layer1, layer2, delta):
        """
        Apply the kerning difference to the given layer pair.
        """
        # TODO: Support RTL kerning
        # TODO: Support exceptions

        # layer1Exception = self.windowController().AltKey()
        # layer2Exception = self.windowController().CommandKey()
        master = layer2.master
        masterId = master.id
        font = master.font

        glyph1Key = layer1.parent.rightKerningKey
        glyph2Key = layer2.parent.leftKerningKey

        # classKerning = font.kerningForPair(masterId, glyph1Key, glyph2Key)

        kerning = font.kerningForPair(masterId, glyph1Key, glyph2Key)
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

        font.setKerningForPair(
            masterId,
            glyph1Key,
            glyph2Key,
            kerning,
        )

    @objc.python_method
    def __file__(self):
        """Please leave this method unchanged"""
        return __file__
