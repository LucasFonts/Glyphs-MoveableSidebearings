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
        self.active_metric = None
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
        # objc.super(DragToKern, self).mouseDown_(theEvent)
        # Get the mouse click location and convert it to local coordinates
        gv = self.editViewController().graphicView()
        loc = gv.convertPoint_fromView_(theEvent.locationInWindow(), None)
        # Which layer is at the mouse click location?
        layerIndex = gv.layerIndexForPoint_(loc)
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

        # Note the start coordinates for later
        self.drag_start = loc
        # self.layer1.parent.beginUndo()

    def mouseDragged_(self, theEvent):
        """
        Update the kerning when the mouse is dragged and live update is on.
        """
        # objc.super(DragToKern, self).mouseDragged_(theEvent)
        if not LIVE_UPDATE:
            return

        if self.drag_start is None:
            return

        self.handleDrag(theEvent)

    def mouseUp_(self, theEvent):
        """
        If live update is off, we must update the kerning on mouse up.
        """
        # objc.super(DragToKern, self).mouseUp_(theEvent)
        if not LIVE_UPDATE:
            if self.drag_start is None:
                self.layer1 = None
                self.layer2 = None
                return
            
            self.handleDrag(theEvent)

        # self.layer1.parent.endUndo()
        self.drag_start = None
        self.layer1 = None
        self.layer2 = None

    @objc.python_method
    def handleDrag(self, theEvent):
        """
        Get the current location while the mouse is dragging.
        """
        evc = self.editViewController()
        gv = evc.graphicView()
        loc = gv.convertPoint_fromView_(theEvent.locationInWindow(), None)
        delta = int(round((loc.x - self.drag_start.x) / evc.scale))
        self.drag_start = loc
        if delta != 0:
            self.applyKerning(self.layer1, self.layer2, delta)

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
