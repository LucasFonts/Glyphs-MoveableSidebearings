# encoding: utf-8
from __future__ import division, print_function, unicode_literals

import objc
from AppKit import (
    NSBezierPath,
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSPoint,
    NSRect,
    NSString,
)
from GlyphsApp import Glyphs, MOUSEMOVED
from GlyphsApp.plugins import SelectTool


SNAP_TOLERANCE = 5
LIVE_UPDATE = True


class DragToKern(SelectTool):
    @objc.python_method
    def settings(self):
        self.name = Glyphs.localize(
            {
                "en": "Kerning and Spacing",
                "de": "Unterschneidung und Zurichtung",
            }
        )
        self.keyboardShortcut = "k"

    @objc.python_method
    def start(self):
        self.dragged_layer = None
        self.active_metric = None
        self.drag_start = None
        self.dragging = False
        self.mouse_position = (0, 0)

    @objc.python_method
    def activate(self):
        # Glyphs.addCallback(self.mouseDidMove, MOUSEMOVED)
        # self.editViewController().graphicView().setActiveIndex_(-1)
        pass

    @objc.python_method
    def deactivate(self):
        # Glyphs.removeCallback(self.mouseDidMove, MOUSEMOVED)
        pass

    @objc.python_method
    def getScale(self):
        # Is only implemented in ReporterPlugin?
        return self.editViewController().scale

    @objc.python_method
    def foreground(self, layer):
        return

        # Get the mouse position
        try:
            self.mouse_position = (
                self.controller.graphicView().getActiveLocation_(
                    Glyphs.currentEvent()
                )
            )
        except Exception as e:
            self.logToConsole("foreground: mouse_position: %s" % str(e))
            self.mouse_position = (0, 0)

        x, y = self.mouse_position

        if self.dragging:
            metricsLocked = self.metricsAreLocked(layer)
            if metricsLocked:
                side = self.active_metric[0]
                if side == "LSB":
                    x = 0.5
                elif side == "RSB":
                    x = layer.width - 0.5

            dist = self.getDraggedDistance()
            # Live update the change
            # if not metricsLocked:
            #     self.setMetrics(self.active_metric, dist)

            # Draw the dragging handle

            self._drawHandle(
                handle_x=(x, 1),
                width=1 / self.getScale(),
                metric=(self.active_metric[0], dist, layer),
                alpha=1.0,
                locked=metricsLocked,
            )
            return

        # Is the mouse inside the "hot spot"?
        # If yes, display drag handles

        try:
            master = layer.master
        except KeyError:
            return

        if y < master.descender or y > master.ascender:
            self.active_metric = None
            return

        if x < 0 or x > layer.width:
            # Mouse is outside the glyph
            self.active_metric = None
            return

        snap_tolerance = SNAP_TOLERANCE / self.getScale()

        if x > snap_tolerance and x < layer.width - snap_tolerance:
            # Mouse is too far inside the glyph
            self.active_metric = None
            return

        if x < snap_tolerance:
            handle_x = (0, snap_tolerance)
            metric = ("LSB", layer.LSB, layer)
        else:
            handle_x = (layer.width - snap_tolerance, snap_tolerance)
            metric = ("RSB", layer.RSB, layer)
        self.active_metric = metric
        self._drawHandle(handle_x, snap_tolerance, metric)

    @objc.python_method
    def _drawHandle(self, handle_x, width, metric, alpha=0.3, locked=False):
        pos, _ = handle_x
        master = metric[2].master
        NSColor.colorWithCalibratedRed_green_blue_alpha_(
            0.9, 0.1, 0.0, alpha
        ).set()
        rect = NSRect(
            origin=(pos, master.descender),
            size=(width, master.ascender - master.descender),
        )
        NSBezierPath.bezierPathWithRect_(rect).fill()
        self._drawTextLabel(handle_x, width, metric, alpha, locked)

    @objc.python_method
    def _drawTextLabel(self, handle_x, width, metric, alpha=0.3, locked=False):
        scale = self.getScale()
        text_size = 11 / scale
        text_dist = 5 / scale
        metric_name, value, layer = metric
        if locked:
            shown_value = "🔒︎"
        elif metric_name == "LSB" and self.dragging:
            shown_value = "∆%g = %g" % (value, layer.LSB - value)
        elif metric_name == "RSB" and self.dragging:
            shown_value = "∆%g = %g" % (value, layer.RSB + value)
        else:
            shown_value = "%g" % value

        attrs = {
            NSFontAttributeName: NSFont.systemFontOfSize_(text_size),
            NSForegroundColorAttributeName: NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.9, 0.1, 0.0, alpha
            ),
        }
        myString = NSString.string().stringByAppendingString_(shown_value)
        bbox = myString.sizeWithAttributes_(attrs)
        bw = bbox.width
        bh = bbox.height

        text_pt = NSPoint()
        text_pt.y = self.mouse_position[1]
        if metric_name == "LSB":
            if self.dragging:
                text_pt.x = handle_x[0] + text_dist
            else:
                text_pt.x = width + text_dist
        elif metric_name == "RSB":
            if self.dragging:
                text_pt.x = handle_x[0] - text_dist - bw
            else:
                text_pt.x = layer.width - width - text_dist - bw
        else:
            text_pt.x = self.mouse_position[0] - text_dist - bw

        rr = NSRect(origin=(text_pt.x, text_pt.y), size=(bw, bh))
        myString.drawInRect_withAttributes_(rr, attrs)

    @objc.python_method
    def getDraggedDistance(self):
        if self.drag_start is None:
            return 0

        return int(round(self.mouse_position[0] - self.drag_start))

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
    def setMetrics(self, metrics, delta):
        if delta == 0:
            return

        side, _, layer = metrics

        if self.metricsAreLocked(layer):
            return

        layer.parent.beginUndo()
        if side == "LSB":
            layer.LSB -= delta
        elif side == "RSB":
            layer.width += delta
        else:
            layer.LSB += delta
            layer.width -= delta
        layer.parent.endUndo()

    @objc.python_method
    def mouseDidMove(self, theEvent):
        # For drawing indicators etc.
        pass
        # Glyphs.redraw()

    def mouseDown_(self, theEvent):
        """
        Do more stuff that you need on mouseDown_(). Like custom selection
        """
        # objc.super(DragToKern, self).mouseDown_(theEvent)
        gv = self.editViewController().graphicView()
        loc = gv.convertPoint_fromView_(theEvent.locationInWindow(), None)
        layerIndex = gv.layerIndexForPoint_(loc)
        if layerIndex > 0xFFFF or layerIndex == 0:
            self.layer1 = None
            self.layer2 = None
            self.drag_start = None
            return

        layers = self.editViewController().composedLayers
        self.layer1 = layers[layerIndex - 1]
        self.layer2 = layers[layerIndex]
        if self.layer2.master != self.layer1.master:
            # Can't add kerning between different masters
            self.layer1 = None
            self.layer2 = None
            self.drag_start = None
            return

        self.drag_start = loc
        # self.layer1.parent.beginUndo()

    def mouseDragged_(self, theEvent):
        """
        Do more stuff that you need on mouseDragged_(). Like moving custom objects
        """
        # objc.super(DragToKern, self).mouseDragged_(theEvent)
        if not LIVE_UPDATE:
            return

        if self.drag_start is None:
            return

        self.handleDrag(theEvent)

    def mouseUp_(self, theEvent):
        # objc.super(DragToKern, self).mouseUp_(theEvent)
        """
        Do more stuff that you need on mouseUp_(). Like custom selection
        """
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
        evc = self.editViewController()
        gv = evc.graphicView()
        loc = gv.convertPoint_fromView_(theEvent.locationInWindow(), None)
        delta = int(round((loc.x - self.drag_start.x) / evc.scale))
        self.drag_start = loc
        if delta != 0:
            self.applyKerning(self.layer1, self.layer2, delta)

    @objc.python_method
    def applyKerning(self, layer1, layer2, delta):
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
        if kerning is None:
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
